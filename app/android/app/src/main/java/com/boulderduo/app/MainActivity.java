package com.boulderduo.app;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(BtLink.class);   // the Bluetooth link for playing on two phones
        super.onCreate(savedInstanceState);
    }
}
