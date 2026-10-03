package com.boulderduo.app;

import android.Manifest;
import android.annotation.SuppressLint;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothServerSocket;
import android.bluetooth.BluetoothSocket;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Two phones, one game: a plain Bluetooth (RFCOMM) link between two phones that are already paired.
 * One phone hosts (waits for the other), the other joins it; then both send and receive lines of text.
 * Events for the page: "connected" {name}, "data" {line}, "closed" {reason}.
 */
@CapacitorPlugin(
    name = "BtLink",
    permissions = { @Permission(alias = "bt", strings = { Manifest.permission.BLUETOOTH_CONNECT }) }
)
public class BtLink extends Plugin {
    private static final UUID GAME = UUID.fromString("6f3b2a10-5c1e-4c7a-9b1d-b0d7e2a1d0f5");
    private BluetoothServerSocket server;
    private BluetoothSocket socket;
    private OutputStream out;
    private final ExecutorService writer = Executors.newSingleThreadExecutor();

    private BluetoothAdapter adapter() {
        BluetoothManager m = (BluetoothManager) getContext().getSystemService(Context.BLUETOOTH_SERVICE);
        return m == null ? null : m.getAdapter();
    }

    // Android 12 and later ask the person for "nearby devices"; before that it is granted at install
    private boolean allowed(PluginCall call) {
        if (Build.VERSION.SDK_INT < 31 || getPermissionState("bt") == PermissionState.GRANTED) return true;
        requestPermissionForAlias("bt", call, "afterPermission");
        return false;
    }

    @PermissionCallback
    private void afterPermission(PluginCall call) {
        if (getPermissionState("bt") != PermissionState.GRANTED) { call.reject("Sin permiso para usar Bluetooth"); return; }
        switch (call.getMethodName()) {
            case "status": status(call); break;
            case "paired": paired(call); break;
            case "host": host(call); break;
            case "join": join(call); break;
            default: call.resolve();
        }
    }

    @SuppressLint("MissingPermission")
    @PluginMethod
    public void status(PluginCall call) {
        if (!allowed(call)) return;
        BluetoothAdapter a = adapter();
        JSObject r = new JSObject();
        r.put("available", a != null);
        r.put("on", a != null && a.isEnabled());
        if (a != null && !a.isEnabled()) {
            // ask Android to turn it on (a system dialog); the page checks again afterwards
            try { getActivity().startActivity(new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)); } catch (Exception e) { /* the person turns it on by hand */ }
        }
        call.resolve(r);
    }

    @SuppressLint("MissingPermission")
    @PluginMethod
    public void paired(PluginCall call) {
        if (!allowed(call)) return;
        BluetoothAdapter a = adapter();
        JSArray list = new JSArray();
        if (a != null && a.isEnabled()) for (BluetoothDevice d : a.getBondedDevices()) {
            JSObject o = new JSObject();
            o.put("name", d.getName() == null ? d.getAddress() : d.getName());
            o.put("address", d.getAddress());
            list.put(o);
        }
        JSObject r = new JSObject();
        r.put("devices", list);
        call.resolve(r);
    }

    @SuppressLint("MissingPermission")
    @PluginMethod
    public void host(PluginCall call) {
        if (!allowed(call)) return;
        BluetoothAdapter a = adapter();
        if (a == null || !a.isEnabled()) { call.reject("El Bluetooth está apagado"); return; }
        closeAll();
        try {
            server = a.listenUsingRfcommWithServiceRecord("Boulder Duo", GAME);
        } catch (IOException e) { call.reject("No se pudo abrir la partida: " + e.getMessage()); return; }
        final BluetoothServerSocket s = server;
        new Thread(() -> {
            try {
                BluetoothSocket got = s.accept();
                try { s.close(); } catch (IOException ignored) { }
                if (server == s) server = null;
                start(got);
            } catch (IOException e) {
                if (server == s) closed("No llegó nadie");
            }
        }, "bt-accept").start();
        call.resolve();
    }

    @SuppressLint("MissingPermission")
    @PluginMethod
    public void join(PluginCall call) {
        if (!allowed(call)) return;
        String address = call.getString("address");
        BluetoothAdapter a = adapter();
        if (a == null || !a.isEnabled()) { call.reject("El Bluetooth está apagado"); return; }
        if (address == null) { call.reject("Falta el celular"); return; }
        closeAll();
        new Thread(() -> {
            try {
                BluetoothDevice d = a.getRemoteDevice(address);
                a.cancelDiscovery();
                BluetoothSocket s = d.createRfcommSocketToServiceRecord(GAME);
                s.connect();
                start(s);
                call.resolve();
            } catch (Exception e) {
                call.reject("No se pudo conectar: ¿el otro celular abrió la partida?");
            }
        }, "bt-join").start();
    }

    @PluginMethod
    public void send(PluginCall call) {
        final String data = call.getString("data", "");
        final OutputStream o = out;
        if (o == null) { call.reject("Sin conexión"); return; }
        writer.execute(() -> {
            try { o.write((data + "\n").getBytes(StandardCharsets.UTF_8)); o.flush(); }
            catch (IOException e) { closed("Se cortó la conexión"); }
        });
        call.resolve();
    }

    @PluginMethod
    public void close(PluginCall call) {
        closeAll();
        call.resolve();
    }

    @SuppressLint("MissingPermission")
    private void start(BluetoothSocket s) throws IOException {
        socket = s;
        out = s.getOutputStream();
        JSObject c = new JSObject();
        BluetoothDevice d = s.getRemoteDevice();
        c.put("name", d == null || d.getName() == null ? "" : d.getName());
        notifyListeners("connected", c);
        final BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8));
        new Thread(() -> {
            try {
                String line;
                while ((line = in.readLine()) != null) {
                    JSObject m = new JSObject();
                    m.put("line", line);
                    notifyListeners("data", m);
                }
                if (socket == s) closed("El otro celular salió");
            } catch (IOException e) {
                if (socket == s) closed("Se cortó la conexión");
            }
        }, "bt-read").start();
    }

    private void closed(String why) {
        closeAll();
        JSObject m = new JSObject();
        m.put("reason", why);
        notifyListeners("closed", m);
    }

    private void closeAll() {
        try { if (server != null) server.close(); } catch (IOException ignored) { }
        try { if (socket != null) socket.close(); } catch (IOException ignored) { }
        server = null; socket = null; out = null;
    }

    @Override
    protected void handleOnDestroy() { closeAll(); }
}
