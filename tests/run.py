"""Executor dos testes. Sem pytest de proposito.

O que e testado aqui nao tem dependencia nenhuma alem da biblioteca padrao, e o CI
nao deveria precisar de mais que o interpretador para provar isso. Instalar um
runner so para chamar funcoes sem argumento seria pagar uma dependencia pelo que
`getattr` ja faz.

Antes a lista de modulos estava colada dentro do YAML do CI, o que significa que um
arquivo de teste novo nao rodava ate alguem lembrar de edita-lo. Agora a descoberta
e por diretorio.

    python3 tests/run.py
"""

import sys
import traceback
from pathlib import Path


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(raiz))

    modulos = sorted(p.stem for p in (raiz / "tests").glob("test_*.py"))
    if not modulos:
        print("nenhum modulo de teste encontrado", file=sys.stderr)
        return 1

    falhas = 0
    for nome in modulos:
        modulo = __import__(f"tests.{nome}", fromlist=["*"])
        print(f"\n-- {nome}")
        for caso in sorted(x for x in dir(modulo) if x.startswith("test_")):
            try:
                getattr(modulo, caso)()
            except Exception:
                falhas += 1
                print(f"FALHA  {caso}")
                traceback.print_exc()
            else:
                print(f"ok     {caso}")

    print(f"\n{'FALHOU' if falhas else 'OK'} — {falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
