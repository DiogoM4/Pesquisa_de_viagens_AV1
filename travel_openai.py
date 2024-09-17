import requests
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

def obter_dados_voo_google_sheets(spreadsheet_id, range_name, credentials_file):
    credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()

    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])

    if not values:
        print('Nenhum dado encontrado no Google Sheets.')
        return pd.DataFrame()
    else:
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        return df

def obter_token_acesso(client_id, client_secret):
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token_info = response.json()
        return token_info['access_token']
    else:
        print(f"Erro ao obter o token de acesso: {response.status_code}")
        return None

def consultar_previsao_voo(token, departure_airport, arrival_airport, departure_date):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": departure_airport,
        "destinationLocationCode": arrival_airport,
        "departureDate": departure_date,
        "adults": 1,
        "currencyCode": "USD"
    }
    
    print(f"Consultando voo com os parâmetros: {params}")
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Erro ao consultar previsão de voo: {response.status_code} - {response.text}")
        return None

def converter_para_reais(valor_usd):
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    response = requests.get(url)
    
    if response.status_code == 200:
        taxas = response.json().get("rates", {})
        taxa_brl = taxas.get("BRL")
        if taxa_brl:
            valor_brl = valor_usd * taxa_brl
            return valor_brl
        else:
            print("Erro: Taxa de câmbio para BRL não encontrada.")
            return valor_usd
    else:
        print("Erro: Não foi possível obter as taxas de câmbio.")
        return valor_usd

# Função para analisar os preços mínimos e máximos dos voos no DataFrame
def analisar_preco(df_voos, client_id, client_secret):
    token = obter_token_acesso(client_id, client_secret)
    if not token:
        print("Não foi possível obter o token de acesso.")
        return

    for index, row in df_voos.iterrows():
        departure_airport = row['Departure Airport']
        arrival_airport = row['Arrival Airport']
        departure_date = row['Departure Time'].split('T')[0]  # Extrai apenas a data no formato YYYY-MM-DD

        if len(departure_airport) != 3 or len(arrival_airport) != 3:
            print(f"Erro nos códigos IATA: {departure_airport}, {arrival_airport}")
            continue

        response_data = consultar_previsao_voo(token, departure_airport, arrival_airport, departure_date)
        
        if response_data and 'data' in response_data and len(response_data['data']) > 0:
            # Inicializa os preços mínimo e máximo
            preco_minimo_usd = float('inf')
            preco_maximo_usd = float('-inf')
            
            # Percorre todas as ofertas de voo
            for oferta in response_data['data']:
                preco_atual = float(oferta['price']['total'])
                # Atualiza o preço mínimo e máximo
                if preco_atual < preco_minimo_usd:
                    preco_minimo_usd = preco_atual
                if preco_atual > preco_maximo_usd:
                    preco_maximo_usd = preco_atual

            # Converte os preços para reais
            preco_minimo_brl = converter_para_reais(preco_minimo_usd)
            preco_maximo_brl = converter_para_reais(preco_maximo_usd)

            print(f"Para o voo {row['Flight Number']}, o preço mínimo é: {preco_minimo_usd:.2f} USD ({preco_minimo_brl:.2f} BRL) e o preço máximo é: {preco_maximo_usd:.2f} USD ({preco_maximo_brl:.2f} BRL)")
        else:
            print(f"Não foi possível obter informações de preço para o voo {row['Flight Number']}")

# Configurações da planilha do Google Sheets
SPREADSHEET_ID = '1ucL0YO8ESBap5R5vshfor2QR7c4GY_kHzjw45C74tyA'
RANGE_NAME = 'Folha1!A1:H'
CREDENTIALS_FILE = 'cred.json'

client_id = 'rle7Y4zFOwBC2zmjPAexvMeAVgIzzGWZ'
client_secret = 'OYpsZdhoSX4OVkpR'

if __name__ == "__main__":
    df_voos = obter_dados_voo_google_sheets(SPREADSHEET_ID, RANGE_NAME, CREDENTIALS_FILE)

    if not df_voos.empty:
        analisar_preco(df_voos, client_id, client_secret)
    else:
        print("Nenhum dado de voo disponível para análise.")
