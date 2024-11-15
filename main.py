import requests
from datetime import datetime


class SolscanScraper:
    def __init__(self, main_address, from_addresses, to_addresses, avoided_tokens):
        self.main_address = main_address
        self.from_addresses = from_addresses
        self.to_addresses = to_addresses
        self.avoided_tokens = avoided_tokens
        self.rpc_url = "https://api.mainnet-beta.solana.com/"

    def extractTransfers(self, n=10):
        signatures = self.fetch_transaction_signatures(n)
        transfers = self.get_transfers_from_signatures(signatures)
        filtered_transfers = self.filter_transfers(transfers)
        return filtered_transfers

    def fetch_transaction_signatures(self, n):
        """Fetches the last n transaction signatures for the main_address."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [self.main_address, {"limit": n}]
        }

        response = requests.post(self.rpc_url, json=payload)
        if response.status_code == 200:
            return [entry['signature'] for entry in response.json()['result']]
        else:
            raise Exception(f"Error fetching signatures: {response.status_code}, {response.text}")

    def get_transfers_from_signatures(self, signatures):
        """Fetches detailed transaction info for each signature."""
        transfers = []
        for signature in signatures:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getConfirmedTransaction",
                "params": [signature]
            }
            response = requests.post(self.rpc_url, json=payload)
            if response.status_code == 200:
                transaction_data = response.json().get('result', {})
                transfer = self.extract_transfer_info(transaction_data)
                if transfer:
                    transfers.append(transfer)
        return transfers

    def extract_transfer_info(self, transaction_data):
        message = transaction_data.get('transaction', {}).get('message', {})
        meta = transaction_data.get('meta', {})

        if not message or not meta:
            return None

        instructions = message.get('instructions', [])
        for instr in instructions:
            if instr.get('programId') == 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA':
                transfer = {
                    'signature': transaction_data['transaction']['signatures'][0],
                    'from_address': message['accountKeys'][instr['accounts'][0]],
                    'to_address': message['accountKeys'][instr['accounts'][1]],
                    'date': datetime.utcfromtimestamp(meta['blockTime']).strftime('%Y-%m-%d %H:%M:%S'),
                    'token_symbol': self.get_token_symbol(instr['accounts'][2]),
                    'token_address': instr['accounts'][2],
                    'amount': self.decode_amount(instr['data'])
                }
                return transfer
        return None

    def decode_amount(self, data):

        return int(data, 16) / (10 ** 6)

    def get_token_symbol(self, token_address):

        token_mapping = {
            'Dez263...': 'BONK',
            'TokenUSDC...': 'USDC',

        }
        return token_mapping.get(token_address, 'Unknown')

    def filter_transfers(self, transfers):

        filtered = []

        for txn in transfers:

            if txn['token_symbol'] in self.avoided_tokens:
                continue


            if txn['from_address'] in self.from_addresses:
                txn_type = 'buy'
            elif txn['from_address'] == self.main_address:
                txn_type = 'sell'
            else:
                continue

            filtered.append({
                'type': txn_type,
                'signature': txn['signature'],
                'from_address': txn['from_address'],
                'to_address': txn['to_address'],
                'date': txn['date'],
                'token_symbol': txn['token_symbol'],
                'token_address': txn['token_address'],
                'amount': txn['amount']
            })

        return filtered


# Usage
main_address = 'EjwYJMj7wyP9w29WttYBSfh4dfFSuCFiSpAmjhiU72yp'
from_addresses = [
    'CapuXNQoDviLvU1PxFiizLgPNQCxrsag1uMeyk6zLVps',
    'GGztQqQ6pCPaJQnNpXBgELr5cs3WwDakRbh1iEMzjgSJ'
]
to_addresses = from_addresses
avoided_tokens = ['USDC', 'USDT', 'SOL', 'WSOL']

scraper = SolscanScraper(main_address, from_addresses, to_addresses, avoided_tokens)
transfers = scraper.extractTransfers(n=10)

for transfer in transfers:
    print(transfer)
