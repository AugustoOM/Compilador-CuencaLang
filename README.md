# CuencaLang Compiler

Compilador didactico para el TPI de Teoria de la Computacion.
Compila un lenguaje propio llamado **CuencaLang** a Python 3.

## Uso en terminal

```bash
python cuencalang_compiler.py examples/oferta_demanda.clg -o oferta_demanda_generado.py
python oferta_demanda_generado.py
```

Para ver los tokens reconocidos:

```bash
python cuencalang_compiler.py examples/oferta_demanda.clg --tokens
```

## Fases implementadas

1. Analisis lexico: convierte el codigo fuente en tokens.
2. Analisis sintactico: construye un AST con descenso recursivo.
3. Analisis semantico: valida declaraciones, tipos y condiciones.
4. Generacion de codigo: emite Python equivalente.

## Ejemplo de dominio

El ejemplo principal calcula una situacion de oferta y demanda: compara oferta disponible con demanda, calcula excedente y ejecuta un ciclo hasta acercar la demanda al nivel de oferta.
