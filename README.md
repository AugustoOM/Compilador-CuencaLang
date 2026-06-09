# CuencaLang Compiler + CuencaVM

Trabajo Practico Integrador de Teoria de la Computacion.

Este proyecto implementa un lenguaje propio llamado **CuencaLang** y un compilador propio que genera **CuencaBytecode**, un codigo intermedio disenado para el trabajo. El bytecode se ejecuta con **CuencaVM**, una maquina virtual propia basada en pila.

## Flujo real

```txt
CuencaLang (.clg)
  -> Lexer
  -> Tokens
  -> Parser
  -> AST
  -> Analisis semantico
  -> Generador de CuencaBytecode (.cbc)
  -> CuencaVM
  -> Salida del programa
```

El compilador esta implementado en Python como herramienta de desarrollo, pero **Python no es el lenguaje destino**. El lenguaje destino es CuencaBytecode.

## Archivos principales

```txt
cuencalang.py                 Compilador + VM
examples/oferta_demanda.clg   Programa valido principal
examples/ahorro_simple.clg    Segundo programa valido
tests/test_cuencalang.py      Pruebas automaticas
```

## Uso

Compilar un programa fuente a bytecode:

```bash
python cuencalang.py compile examples/oferta_demanda.clg -o oferta_demanda.cbc --dis
```

Ejecutar directamente un programa fuente:

```bash
python cuencalang.py run examples/oferta_demanda.clg
```

Ejecutar bytecode ya compilado:

```bash
python cuencalang.py run oferta_demanda.cbc
```

Ver tokens y AST:

```bash
python cuencalang.py compile examples/oferta_demanda.clg --tokens --ast
```

Desensamblar bytecode:

```bash
python cuencalang.py dis oferta_demanda.cbc
```

## Fases implementadas

1. Analisis lexico: convierte caracteres en tokens.
2. Analisis sintactico: valida la gramatica y construye un AST.
3. Analisis semantico: valida declaracion de variables, tipos y condiciones.
4. Generacion de codigo intermedio: emite instrucciones CuencaBytecode.
5. Ejecucion en maquina virtual: CuencaVM ejecuta el bytecode con una pila y memoria propia.

## Instrucciones de bytecode

Algunas instrucciones usadas por CuencaBytecode:

- `PUSH valor`
- `DECLARE {name, type}`
- `STORE variable`
- `LOAD variable`
- `ADD`, `SUB`, `MUL`, `DIV`
- `LT`, `GT`, `LE`, `GE`, `EQ`, `NE`
- `AND`, `OR`, `NOT`, `NEG`
- `JMP direccion`
- `JMP_IF_FALSE direccion`
- `PRINT`
- `HALT`

## Ejecutar pruebas

```bash
python -m unittest discover -s tests -v
```
