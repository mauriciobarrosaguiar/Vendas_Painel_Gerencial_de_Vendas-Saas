from __future__ import annotations

import re

from .tratamento import normalizar_texto_alto


REGRAS_MOLECULAS = [
    ("AMOXICILINA+CLAVULANATO", ("AMOXICILINA", "CLAVULANATO")),
    ("CLORIDRATO DE DULOXETINA", ("DULOXETINA",)),
]

ABREVIACOES_MOLECULAS = {
    "AMOXICILINA+CLAVULANATO": "AMOX+CLAV",
    "CLORIDRATO DE DULOXETINA": "DULOXETINA",
}

MARCADORES_APRESENTACAO = (
    " CPR ",
    " CAPS ",
    " CAP ",
    " COM ",
    " CAIXA ",
    " FRASCO ",
    " PO ",
    " P\u00d3 ",
    " SUS ",
    " ORAL ",
    " MG ",
    " ML ",
    " X ",
    " C/ ",
    " REVESTIDO ",
    " LIB RET ",
)


def identificar_molecula(produto: object) -> str:
    texto = normalizar_texto_alto(produto)
    if not texto:
        return "PRODUTO SEM DESCRICAO"

    for nome, termos in REGRAS_MOLECULAS:
        if all(termo in texto for termo in termos):
            return nome

    texto_padrao = f" {texto} "
    cortes = [texto_padrao.find(marcador) for marcador in MARCADORES_APRESENTACAO if texto_padrao.find(marcador) > 0]
    if cortes:
        texto = texto_padrao[: min(cortes)].strip()
    texto = re.sub(r"\b\d+([,.]\d+)?\s*(MG|ML|G|MCG|UI)\b.*", "", texto).strip()
    texto = re.sub(r"\s+", " ", texto).strip(" -+/")
    return texto or normalizar_texto_alto(produto)[:45]


def abreviar_molecula(molecula: object) -> str:
    nome = normalizar_texto_alto(molecula)
    if nome in ABREVIACOES_MOLECULAS:
        return ABREVIACOES_MOLECULAS[nome]
    return nome[:22] if len(nome) > 22 else nome

