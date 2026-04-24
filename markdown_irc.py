#!/usr/bin/env python3
"""
Conversão básica de Markdown/LaTeX para texto compatível com IRC.
"""

import re


def convert_markdown_to_irc(text):
    if not text:
        return text

    # -------------------------
    # 1. LaTeX básico -> texto simples
    # -------------------------

    # normaliza double braces {{ }} -> { }
    text = re.sub(r'\{\{+', '{', text)
    text = re.sub(r'\}\}+', '}', text)

    # blocos \[...\] e \(...\)
    text = re.sub(r'\\\[(.*?)\\\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text, flags=re.DOTALL)

    # aplica mais de uma vez para lidar com aninhamento simples
    for _ in range(3):
        # \frac{a}{b} -> (a)/(b)
        text = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'(\1)/(\2)', text)

        # \sqrt{x} -> √(x)
        text = re.sub(r'\\sqrt\{([^{}]+)\}', r'√(\1)', text)

    latex_replacements = {
        r'\pm': '±',
        r'\cdot': '·',
        r'\times': '×',
        r'\neq': '≠',
        r'\leq': '≤',
        r'\geq': '≥',
        r'\approx': '≈',
        r'\degree': '°',
    }

    for original, replacement in latex_replacements.items():
        text = text.replace(original, replacement)

    # potências simples mais comuns
    text = text.replace("^2", "²")
    text = text.replace("^3", "³")

    # remove escapes simples restantes do LaTeX
    text = re.sub(r'\\([{}])', r'\1', text)

    # remove comandos LaTeX residuais simples
    text = re.sub(r'\\[a-zA-Z]+', '', text)

    # -------------------------
    # 2. Code blocks e inline code
    # -------------------------

    # ```lang\n...\n``` -> remove fences e mantém só conteúdo
    text = re.sub(
        r'```[a-zA-Z0-9_-]*\n(.*?)```',
        lambda m: m.group(1).strip(),
        text,
        flags=re.DOTALL,
    )

    # ```...``` genérico -> mantém só conteúdo
    text = re.sub(
        r'```(.*?)```',
        lambda m: m.group(1).strip(),
        text,
        flags=re.DOTALL,
    )

    # `inline code` -> monospace IRC (\x11 funciona em alguns clientes)
    text = re.sub(
        r'`([^`]+)`',
        lambda m: "\x11" + m.group(1) + "\x11",
        text,
    )

    # -------------------------
    # 3. Markdown que vale converter
    # -------------------------

    # links [texto](url) -> texto (url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)

    # **_texto_** -> bold
    text = re.sub(
        r'\*\*_([^*]+)_\*\*',
        lambda m: "\x02" + m.group(1) + "\x02",
        text,
    )

    # **texto** -> bold
    text = re.sub(
        r'\*\*(.*?)\*\*',
        lambda m: "\x02" + m.group(1) + "\x02",
        text,
    )

    # __texto__ -> underline IRC
    # Usa marcador temporário para impedir que a regra posterior de itálico
    # com "_" remova o caractere IRC de fechamento.
    text = re.sub(
        r'__(.*?)__',
        lambda m: "\x00U" + m.group(1) + "\x00U",
        text,
    )

    # -------------------------
    # 4. Markdown que vale limpar/simplificar
    # -------------------------

    # itálico com *texto* ou _texto_ -> remove as marcas
    text = re.sub(r'(?<!\*)\*(?!\*)([^*]+)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)([^_]+)(?<!_)_(?!_)', r'\1', text)

    # ~~riscado~~ -> remove marcação
    text = re.sub(r'~~(.*?)~~', r'\1', text)

    # headings markdown (#, ##, ###...) -> remove os #
    text = re.sub(r'^\s*#{1,6}\s*', '', text, flags=re.MULTILINE)

    # blockquote > -> remove o >
    text = re.sub(r'^\s*>\s?', '', text, flags=re.MULTILINE)

    # listas simples: mantém como texto normal, só normaliza bullet
    text = re.sub(r'^\s*[-*+]\s+', '• ', text, flags=re.MULTILINE)

    # -------------------------
    # 5. Limpeza final
    # -------------------------

    # remove escapes markdown remanescentes
    text = text.replace(r'\*', '*')
    text = text.replace(r'\_', '_')
    text = text.replace(r'\`', '`')
    text = text.replace(r'\~', '~')
    text = text.replace(r'\#', '#')
    text = text.replace(r'\[', '[')
    text = text.replace(r'\]', ']')
    text = text.replace(r'\(', '(')
    text = text.replace(r'\)', ')')

    # restaura underline IRC
    text = text.replace("\x00U", "\x1F")

    # corrige espaços antes de pontuação
    text = re.sub(r'\s+([,.;:!?])', r'\1', text)

    # colapsa espaços excessivos sem destruir quebras úteis
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # trim só de whitespace, sem tocar em controle IRC
    text = text.strip(" \t\r\n")
    return text
