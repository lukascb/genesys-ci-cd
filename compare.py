#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de sincronização de templates, extração de variáveis e merge de dados.
Código: Qwen
"""

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple


def normalize_line(line: str) -> str:
    """
    Aplica a Regra de Igualdade Flexível.
    Remove TODOS os espaços, tabs e quebras de linha (\n, \r) da string.
    Garante que 'KEY : VAL' e 'KEY:VAL' se tornem equivalentes.
    """
    # \s+ cobre espaços, \t, \n, \r e outros caracteres de whitespace unicode
    return re.sub(r'\s+', '', line)


def extract_key_value(norm_line: str) -> Optional[Tuple[str, str]]:
    """
    Extrai chave e valor a partir do primeiro separador ':'.
    Retorna None se o separador não for encontrado.
    """
    if ':' not in norm_line:
        return None
    key, value = norm_line.split(':', 1)
    return key, value


def extract_placeholder_name(text: str) -> Optional[str]:
    """
    Identifica e extrai o nome interno de um placeholder {{NOME_VAR}}.
    """
    match = re.search(r'\{\{(.+?)\}\}', text)
    return match.group(1) if match else None


def load_vars_file(filepath: str) -> Dict[str, str]:
    """
    Carrega o arquivo de variáveis existente para um dicionário.
    Ignora linhas vazias, comentários ou formatos inválidos.
    """
    if not os.path.exists(filepath):
        return {}
    
    vars_dict: Dict[str, str] = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    vars_dict[key.strip()] = val.strip().strip('"')
    except (IOError, OSError) as e:
        print(f"Warning: Falha ao ler {filepath}. Iniciando repositório vazio. ({e})", file=sys.stderr)
    return vars_dict


def save_vars_file(filepath: str, data: Dict[str, str]) -> None:
    """
    Persiste o dicionário no formato VAR_NAME = "valor".
    Sobrescreve o arquivo para garantir consistência e unicidade lógica.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for var_name, value in data.items():
                f.write(f'{var_name} = "{value}"\n')
    except PermissionError as e:
        print(f"Error: Permissão negada para escrever em {filepath}. ({e})", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error: Falha de I/O ao salvar {filepath}. ({e})", file=sys.stderr)
        sys.exit(1)

def sanitize_empty_quotes(filepath: str = "vars.txt") -> None:
    """
    Abre o arquivo de variáveis e substitui todas as ocorrências de '""' por '"'.
    
    Arquitetura:
    - Processamento em Stream: Evita carregamento total em memória (O(1) space).
    - Escrita Atômica: Utiliza arquivo temporário + os.replace para prevenir corrupção.
    - Segurança I/O: Context managers e tratamento granular de exceções.
    """
    if not os.path.exists(filepath):
        print(f"Warning: Arquivo '{filepath}' não encontrado. Operação abortada.", file=sys.stderr)
        return

    temp_filepath = f"{filepath}.tmp"
    try:
        # Leitura e escrita simultâneas via stream (baixo consumo de RAM)
        with open(filepath, 'r', encoding='utf-8') as f_in, \
             open(temp_filepath, 'w', encoding='utf-8') as f_out:
            
            for line in f_in:
                # Substituição de todas as ocorrências na linha
                f_out.write(line.replace('""', '"'))

        # Substituição atômica: garante integridade mesmo em falhas de disco/energia
        os.replace(temp_filepath, filepath)
        print(f"Substituição concluída com sucesso em '{filepath}'.", file=sys.stderr)

    except UnicodeDecodeError as e:
        print(f"Error: Codificação inválida (esperado UTF-8). ({e})", file=sys.stderr)
        _cleanup_temp(temp_filepath)
        sys.exit(1)
        
    except PermissionError as e:
        print(f"Error: Permissão negada para ler/escrever '{filepath}'. ({e})", file=sys.stderr)
        _cleanup_temp(temp_filepath)
        sys.exit(1)
        
    except OSError as e:
        print(f"Error: Falha de I/O durante processamento. ({e})", file=sys.stderr)
        _cleanup_temp(temp_filepath)
        sys.exit(1)


def _cleanup_temp(temp_path: str) -> None:
    """Remove arquivo temporário em caso de falha para evitar lixo no disco."""
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except OSError:
            pass  # Ignora falhas na limpeza para não mascarar a exceção original


def main() -> None:
    # 1. Interface CLI
    parser = argparse.ArgumentParser(
        description="Sincronização de templates, extração de variáveis e merge de dados.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-f1", "--file-base", required=True, help="Arquivo de referência (template com placeholders).")
    parser.add_argument("-f2", "--file-new", required=True, help="Arquivo com dados reais para comparação/merge.")
    parser.add_argument("-o", "--output", default="template_gerado.yaml", help="Caminho do arquivo de template gerado.")
    parser.add_argument("-v", "--vars-file", default="vars.txt", help="Caminho do arquivo de persistência de variáveis.")
    
    args = parser.parse_args()

    # 2. Leitura Segura com Context Managers
    try:
        with open(args.file_base, 'r', encoding='utf-8') as f_base, \
             open(args.file_new, 'r', encoding='utf-8') as f_new:
            base_raw_lines: List[str] = f_base.readlines()
            new_raw_lines: List[str] = f_new.readlines()
    except FileNotFoundError as e:
        print(f"Error: Arquivo não encontrado -> {e.filename}", file=sys.stderr)
        sys.exit(1)
    except PermissionError as e:
        print(f"Error: Permissão negada -> {e.filename}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: Codificação inválida (esperado UTF-8) -> {e.filename}", file=sys.stderr)
        sys.exit(1)

    # 3. Construção de Mapas Hash (Complexidade O(N+M) - Busca O(1))
    base_key_map: Dict[str, str] = {}
    new_key_map: Dict[str, str] = {}
    base_keys_set: Set[str] = set()
    new_keys_set: Set[str] = set()

    for line in base_raw_lines:
        norm = normalize_line(line)
        kv = extract_key_value(norm)
        if kv:
            base_key_map[kv[0]] = kv[1]
            base_keys_set.add(kv[0])

    for line in new_raw_lines:
        norm = normalize_line(line)
        kv = extract_key_value(norm)
        if kv:
            new_key_map[kv[0]] = kv[1]
            new_keys_set.add(kv[0])

    # 4. Extração de Variáveis & Validação de Duplicatas
    extracted_vars: Dict[str, str] = {}
    seen_placeholders: Set[str] = set()
    vars_extracted_count = 0

    for line in base_raw_lines:
        norm = normalize_line(line)
        placeholder = extract_placeholder_name(norm)
        if not placeholder:
            continue

        # Gestão de Duplicatas (Set O(1))
        if placeholder in seen_placeholders:
            print(f"Warning: Variável duplicada '{placeholder}' detectada. Ignorando.", file=sys.stderr)
            continue
        seen_placeholders.add(placeholder)

        # Busca O(1) no mapa do arquivo novo
        kv_base = extract_key_value(norm)
        if not kv_base:
            continue
            
        base_key = kv_base[0]
        if base_key not in new_key_map:
            print(f"Warning: Chave '{base_key}' ausente no arquivo novo (-f2).", file=sys.stderr)
            continue

        new_value = new_key_map[base_key]

        # Regra Crítica: Valor não pode conter placeholders
        if re.search(r'\{\{.*?\}\}', new_value):
            print(f"Warning: Valor da chave '{base_key}' ainda contém placeholder. Extração ignorada.", file=sys.stderr)
            continue

        extracted_vars[placeholder] = new_value
        vars_extracted_count += 1

    # Persistência com Merge Seguro
    existing_vars = load_vars_file(args.vars_file)
    existing_vars.update(extracted_vars)  # dict.update garante sobrescrita atômica
    save_vars_file(args.vars_file, existing_vars)
    sanitize_empty_quotes(args.vars_file)  # Limpeza de aspas vazias após atualização

    # 5. Geração do Template Sincronizado
    output_lines = list(base_raw_lines)  # Preservação exata do template base
    
    # Diferença de Conjuntos O(K)
    new_only_keys = new_keys_set - base_keys_set
    lines_added_count = 0
    
    # Append determinístico mantendo a ordem original do -f2
    for line in new_raw_lines:
        norm = normalize_line(line)
        kv = extract_key_value(norm)
        if kv and kv[0] in new_only_keys:
            output_lines.append(line)
            new_only_keys.discard(kv[0]) # Evita duplicação de novas chaves presentes múltiplas vezes em -f2
            lines_added_count += 1

    try:
        with open(args.output, 'w', encoding='utf-8') as f_out:
            f_out.writelines(output_lines)
    except OSError as e:
        print(f"Error: Falha ao gerar template de saída {args.output}. ({e})", file=sys.stderr)
        sys.exit(1)

    # 6. Resumo Final (stdout)
    print(f"Sincronização concluída com sucesso.")
    print(f"Variáveis extraídas: {vars_extracted_count}")
    print(f"Novas linhas somadas: {lines_added_count}")
    print(f"Template salvo em: {args.output}")


if __name__ == "__main__":
    main()



# PROMPT    
# Atue como um Engenheiro de Software Sênior. Desenvolva um script Python de alta performance para sincronização de arquivos de template, extração de variáveis e merge de dados. O código deve ser modular, tipado e seguir rigorosamente as especificações abaixo:

# 1. Interface de Linha de Comando (CLI)
# Utilize argparse com ArgumentDefaultsHelpFormatter para gerar documentação automática de ajuda.

# Argumentos Obrigatórios: -f1 (base/template) e -f2 (novo/dados).

# Argumentos Opcionais: -o (output do template, default: template_gerado.txt) e -v (arquivo de variáveis, default: vars.txt).

# 2. Arquitetura e Performance (Eficiência Algorítmica)
# Complexidade O(1): Proíba loops aninhados para busca. Construa mapas de hash (base_key_map e new_key_map) durante a leitura inicial.

# Normalização: Implemente uma função normalize_line(line: str) -> str que remove todos os espaços, tabs e quebras de linha. Utilize-a antes de qualquer comparação ou extração de chaves.

# Processamento de Chaves: A chave é o conteúdo antes do primeiro :. Garanta que KEY : VAL e KEY:VAL sejam tratados como equivalentes através da normalização.

# 3. Regras de Negócio e Lógica de Extração
# Extração de Variáveis:

# Se uma linha em -f1 contém {{VAR_NAME}}, extraia o nome da variável.

# Busque o valor correspondente no new_key_map (arquivo -f2).

# Regra Crítica: O valor extraído nunca deve conter placeholders {{...}}. Se o valor em -f2 ainda for um placeholder, ignore a extração para esta chave.

# Gestão de Duplicatas: Utilize um set para detecção imediata em memória. Se houver tentativa de duplicata de chave de variável, emita um Warning no console indicando o nome da chave.

# Persistência: O arquivo vars.txt deve conter o mapeamento VAR_NAME = "valor". Utilize dict.update() para garantir um merge seguro antes da escrita final.

# 4. Sincronização e Geração de Template
# O arquivo de saída (-o) deve iniciar como uma cópia exata das linhas brutas de -f1 (mantendo espaços originais e placeholders).

# Diferença de Conjuntos: Identifique chaves existentes em -f2 que estão ausentes em -f1 via set subtraction.

# Append: Anexe essas novas linhas (integrais, conforme aparecem em -f2) ao final do arquivo gerado.

# 5. Robustez e Segurança (I/O)
# Gestão de Arquivos: Use with open() com encoding='utf-8'.

# Tratamento de Erros: Implemente blocos try-except granulares para FileNotFoundError, PermissionError e UnicodeDecodeError.

# Streams de Saída: Mensagens de erro e warnings devem ser direcionadas para sys.stderr.

# Qualidade do Código:

# Aplique Type Hinting (Dict, List, Optional, Tuple).

# Siga o princípio da Responsabilidade Única (SRP) com funções atômicas.

# Inclua Docstrings explicativas em cada função.