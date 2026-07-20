import re
import json
from pathlib import Path

# Definição dos dados brutos fornecidos pelo usuário
DADOS_CONTAS = """
CorwinWellner21@hotmail.com:Yq0x6JzH
CorwinWellner21:Yq0x6JzH
https://www.browserscan.net/2fa#ZMKQUH5YK3CZTFO7OJIXNOBE3CKNM4SK
ZMKQ UH5Y K3CZ TFO7 OJIX NOBE 3CKN M4SK
09:19


ArehartAye8391@hotmail.com:0WsoTRP8x
ArehartAye8391:0WsoTRP8x
YBZKU6P3STMPA2PKQ6NB5NC7J7EGU6IC
https://www.browserscan.net/2fa#YBZKU6P3STMPA2PKQ6NB5NC7J7EGU6IC
09:19


TotiGuzy7536@hotmail.com:xvLGa0BfgM
TotiGuzy7536:xvLGa0BfgM
SFWN6JZ2RH7MULU4PLOCSPXAEU25M7KT
https://www.browserscan.net/2fa#SFWN6JZ2RH7MULU4PLOCSPXAEU25M7KT
09:19


SchreimannBrunkhorst431@hotmail.com:oB5C77afR6w
SchreimannBrunkhorst431:oB5C77afR6w
WAPN 5YHH UZDD R3WD EA3A SUSY 2HNF 2AJU
https://www.browserscan.net/2fa#WAPN5YHHUZDDR3WDEA3ASUSY2HNF2AJU
09:19


TaggertSimo16@hotmail.com:ezdN9Z0IM
TaggertSimo16 Senha: ezdN9Z0IM
2 fatores: 7PCX UHOE EGKC I3GS JV2H BPTF Q64Y UEHC
https://www.browserscan.net/2fa#6QA6KTAFXRA7TBNNSQQY25BMXYIQNAMG
"""

DADOS_PROXIES = """
"104.252.92.46:5980:kghervve:mamb0lpc2rhw"
"104.252.20.112:6044:kghervve:mamb0lpc2rhw"
"104.252.20.206:6138:kghervve:mamb0lpc2rhw"
"185.72.240.10:7046:kghervve:mamb0lpc2rhw"
"45.39.35.126:5559:kghervve:mamb0lpc2rhw"
"108.165.53.231:6970:kghervve:mamb0lpc2rhw"
"45.38.67.197:7129:kghervve:mamb0lpc2rhw"
"23.129.253.191:6809:kghervve:mamb0lpc2rhw"
"""

def extrair_proxies(texto_proxy: str) -> list:
    proxies = []
    linhas = re.findall(r'"?([0-9a-zA-Z\.\-_]+:\d+:\w+:\w+)"?', texto_proxy)
    for linha in list(set(linhas)):
        partes = linha.split(':')
        if len(partes) == 4:
            proxies.append({
                "ip": partes[0],
                "port": int(partes[1]),
                "username": partes[2],
                "password": partes[3],
                "url": f"http://{partes[2]}:{partes[3]}@{partes[0]}:{partes[1]}"
            })
    return proxies

def extrair_contas(texto_contas: str) -> list:
    # Divide os blocos por 2 ou mais quebras de linha consecutivas
    blocos = re.split(r'\n{2,}', texto_contas.strip())
    contas = []
    
    for bloco in blocos:
        linhas = [l.strip() for l in bloco.split('\n') if l.strip()]
        if not list(filter(None, linhas)):
            continue
            
        dados_conta = {
            "email": None,
            "username": None,
            "password": None,
            "totp_secret": None
        }
        
        # Primeiro passe: vamos extrair o e-mail e a senha real do e-mail
        for linha in linhas:
            if '@' in linha and ':' in linha:
                partes = linha.split(':', 1)
                dados_conta["email"] = partes[0].strip()
                dados_conta["password"] = partes[1].strip()
                break
        
        # Segundo passe: extraímos o 2FA e outros metadados, ignorando as linhas de hora (ex: 09:19)
        for linha in linhas:
            # Ignora linhas que são apenas horários como 09:19
            if re.match(r'^\d{2}:\d{2}$', linha):
                continue
                
            # Verifica links de 2FA
            if 'browserscan.net/2fa#' in linha:
                segredo = linha.split('#')[-1].strip()
                dados_conta["totp_secret"] = segredo.replace(" ", "").upper()
                continue
            
            # Verifica formato explícito "2 fatores: ..."
            if '2 fatores:' in linha:
                segredo = linha.split(':', 1)[-1].strip()
                dados_conta["totp_secret"] = segredo.replace(" ", "").upper()
                continue
            
            # Verifica se é uma chave de 2FA pura com espaços (ex: ZMKQ UH5Y K3CZ...)
            linha_limpa = linha.replace(" ", "")
            if linha_limpa.isalnum() and len(linha_limpa) >= 16 and '@' not in linha and ':' not in linha:
                dados_conta["totp_secret"] = linha_limpa.upper()
                
        # Se não encontramos e-mail no bloco mas temos dados mínimos, tenta extrair username/password
        if not dados_conta["email"]:
            for linha in linhas:
                if ':' in linha and not linha.startswith('http') and 'fatores' not in linha.lower():
                    partes = linha.split(':', 1)
                    dados_conta["username"] = partes[0].strip()
                    dados_conta["password"] = partes[1].strip()
                    break

        if dados_conta["email"] and not dados_conta["username"]:
            dados_conta["username"] = dados_conta["email"].split('@')[0]
            
        if dados_conta["email"] or dados_conta["username"]:
            contas.append(dados_conta)
            
    return contas

def principal():
    contas = extrair_contas(DADOS_CONTAS)
    proxies = extrair_proxies(DADOS_PROXIES)
    
    # Associa sequencialmente cada proxy a uma conta para fins de organização
    for i, conta in enumerate(contas):
        if i < len(proxies):
            conta["proxy"] = proxies[i]["url"]
        else:
            conta["proxy"] = None

    caminho_saida = Path(__file__).parent / "contas_configuradas.json"
    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(contas, f, indent=2, ensure_ascii=False)
        
    print(f"[Sucesso] Dados analisados e salvos em: {caminho_saida.resolve()}")

if __name__ == "__main__":
    principal()
