# Codigo Python generado desde CuencaLang: AnalisisMercado
def main():
    oferta = 120
    demanda = 50
    precio = 50
    excedente = (oferta - demanda)
    hay_excedente = (oferta > demanda)
    print("Analisis de oferta y demanda")
    print(excedente)
    if hay_excedente:
        print("Oferta mayor que demanda")
    else:
        print("Demanda mayor o igual a oferta")
    while (demanda < oferta):
        demanda = (demanda + 5)
        print(demanda)

if __name__ == '__main__':
    main()
