import requests
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configurações da API do Amadeus
API_KEY = 'rle7Y4zFOwBC2zmjPAexvMeAVgIzzGWZ'  # Substitua pela sua API Key do Amadeus
API_SECRET = 'OYpsZdhoSX4OVkpR'  # Substitua pelo seu API Secret do Amadeus

# Função para obter o token de acesso da API do Amadeus
def get_access_token(api_key, api_secret):
    url = 'https://test.api.amadeus.com/v1/security/oauth2/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': api_key,
        'client_secret': api_secret
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        raise Exception(f"Falha ao obter o token de acesso: {response.status_code} - {response.text}")

# Função para buscar ofertas de voos usando a Flight Offers Search API
def search_flight_offers(access_token):
    url = 'https://test.api.amadeus.com/v2/shopping/flight-offers'
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    
    # Parâmetros para buscar voos de São Paulo (GRU) para Brasília (BSB)
    params = {
        "originLocationCode": "GRU",
        "destinationLocationCode": "THE",
        "departureDate": "2024-09-27",
        "adults": 1,
        "max": 5  # Limitar o número de resultados para 5
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Falha ao buscar ofertas de voos: {response.status_code} - {response.text}")

# Função para converter moeda usando uma API de taxa de câmbio
def converter_para_reais(valor, moeda_origem):
    # Substitua 'SUA_API_KEY_DE_CAMBIO' pela sua chave de API de câmbio
    url = f"https://api.exchangerate-api.com/v4/latest/{moeda_origem}"
    response = requests.get(url)
    
    if response.status_code == 200:
        taxas = response.json()["rates"]
        taxa_brl = taxas.get("BRL")
        if taxa_brl:
            valor_em_reais = float(valor) * taxa_brl
            print(f"{valor} {moeda_origem} é equivalente a {valor_em_reais:.2f} BRL.")
            return valor_em_reais
        else:
            print("Erro: Taxa de câmbio para BRL não encontrada.")
            return valor
    else:
        print("Erro: Não foi possível obter as taxas de câmbio.")
        return valor

# Função para extrair dados relevantes de voos e converter preços
def extract_flight_data(flight_offers):
    flights = []
    for offer in flight_offers['data']:
        price_usd = offer['price']['grandTotal']  # Preço em USD
        price_brl = converter_para_reais(price_usd, "USD")  # Converter para BRL
        
        for itinerary in offer['itineraries']:
            for segment in itinerary['segments']:
                flight_info = {
                    'Departure Airport': segment['departure']['iataCode'],
                    'Arrival Airport': segment['arrival']['iataCode'],
                    'Departure Time': segment['departure']['at'],
                    'Arrival Time': segment['arrival']['at'],
                    'Carrier': segment['carrierCode'],
                    'Flight Number': segment['number'],
                    'Duration': segment['duration'],
                    'Price (USD)': price_usd,
                    'Price (BRL)': price_brl  # Adiciona o preço convertido para BRL
                }
                flights.append(flight_info)
    return pd.DataFrame(flights)

# Função para atualizar dados no Google Sheets
def update_google_sheets(df, spreadsheet_id, range_name, credentials_file):
    # Configurar credenciais
    credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=['https://www.googleapis.com/auth/spreadsheets'])

    # Conectar ao serviço Google Sheets
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()

    # Converter o DataFrame para uma lista de listas (formato aceito pelo Google Sheets)
    values = [df.columns.tolist()] + df.values.tolist()

    # Preparar o corpo da requisição
    body = {'values': values}

    # Enviar os dados para o Google Sheets
    result = sheet.values().update(spreadsheetId=spreadsheet_id, range=range_name, valueInputOption='RAW', body=body).execute()
    print(f"{result.get('updatedCells')} células atualizadas.")

# Configurações da planilha do Google Sheets
SPREADSHEET_ID = '1ucL0YO8ESBap5R5vshfor2QR7c4GY_kHzjw45C74tyA'  # ID da sua planilha
RANGE_NAME = 'Folha1!A1'  # Faixa de células para atualizar
CREDENTIALS_FILE = 'cred.json'  # Arquivo de credenciais baixado do Google Cloud

# Execução do script
if __name__ == "__main__":
    try:
        # Obter o token de acesso
        token = get_access_token(API_KEY, API_SECRET)
        print("Token de acesso obtido com sucesso.")

        # Buscar ofertas de voos
        flight_offers = search_flight_offers(token)
        print("Ofertas de voos obtidas com sucesso.")

        # Extrair dados de voos para um DataFrame
        df = extract_flight_data(flight_offers)
        print("Dados de voos extraídos e convertidos com sucesso.")

        # Atualizar dados no Google Sheets
        update_google_sheets(df, SPREADSHEET_ID, RANGE_NAME, CREDENTIALS_FILE)
        
    except Exception as e:
        print(f"Erro: {e}")
