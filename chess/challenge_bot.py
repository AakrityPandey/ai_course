"""Send one casual standard 5+3 challenge while start_lichess.py is running."""
import argparse
from urllib.parse import quote

import requests
from lichess_auth import load_token


def check_response(response):
    if response.ok:
        return
    try:
        details = response.json()
        message = details.get('error', details) if isinstance(details, dict) else details
    except ValueError:
        message = response.reason
    raise SystemExit('Lichess HTTP {}: {}'.format(response.status_code, message))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('opponent', help='Lichess BOT username to challenge')
    args = parser.parse_args()
    token = load_token()
    with requests.Session() as session:
        session.headers['Authorization'] = 'Bearer ' + token
        account = session.get('https://lichess.org/api/account', timeout=15)
        check_response(account)
        if account.json().get('title') != 'BOT':
            raise SystemExit('This token must belong to your dedicated BOT account.')
        opponent = quote(args.opponent, safe='')
        profile = session.get('https://lichess.org/api/user/' + opponent, timeout=15)
        check_response(profile)
        if profile.json().get('title') != 'BOT':
            raise SystemExit('Choose an opponent with a BOT account.')
        response = session.post('https://lichess.org/api/challenge/' + opponent,
                                data={'rated': 'false', 'clock.limit': 300,
                                      'clock.increment': 3, 'variant': 'standard'}, timeout=20)
        check_response(response)
        result = response.json()
        challenge = result.get('challenge', result)
        print('Challenge sent:', challenge.get('url') or 'https://lichess.org/' + challenge['id'])
        print('The opponent must accept; keep start_lichess.py running.')


if __name__ == '__main__':
    main()
