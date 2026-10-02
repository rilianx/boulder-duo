"""Catálogo de las plantillas de mecánicas, generado desde el código: python -m boulder.mecanicas [--md]"""
import inspect
import sys

from . import REGISTRO


def filas():
    for cls in REGISTRO:
        doc = (inspect.getmodule(cls).__doc__ or "").strip().replace("\n", " ")
        metodos = [n for n, v in cls.__dict__.items() if callable(v) and not n.startswith("_")]
        yield {
            "nombre": cls.nombre,
            "nucleo": cls.nucleo,
            "estado": ", ".join(cls.estado) or "—",
            "registra": ", ".join(n for n in metodos if n.startswith("record_")) or "—",
            "consultas": ", ".join(n for n in metodos if not n.startswith(("record_", "al_")) and n != "opcion") or "—",
            "eventos": ", ".join(n[3:] for n in metodos if n.startswith("al_")) or "—",
            "opcion": "sí" if cls.orden_opcion is not None else "—",
            "neutro": ", ".join(f"{k}={v!r}" for k, v in cls.neutros.items()) or ("(núcleo)" if cls.nucleo else "—"),
            "doc": doc,
        }


if __name__ == "__main__":
    rows = list(filas())
    if "--md" in sys.argv:
        print("| Mecánica | Núcleo | Estado | Eventos | Consultas | Opción | Apagada devuelve |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            print(f"| **{r['nombre']}** | {'sí' if r['nucleo'] else ''} | {r['estado']} | {r['eventos']} | "
                  f"{r['consultas']} | {r['opcion']} | {r['neutro']} |")
    else:
        for r in rows:
            print(f"{r['nombre']:15s} {'[núcleo] ' if r['nucleo'] else ''}{r['doc']}")
