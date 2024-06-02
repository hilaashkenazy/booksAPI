from itertools import chain

from flask import Flask, request
from flask_restful import Resource, Api, reqparse
import requests

BASE_URL = 'https://openlibrary.org/search.json?q='


def get_languages(ISBN):
    """

    :param ISBN:
    :return:
    """
    response = requests.get(f'{BASE_URL}{ISBN}')
    if response.status_code != 200:
        return {'error': 'Internal Server Error'}, 500

    # Properly parsing the JSON to get all languages
    data = response.json()
    # languages = [doc['language'] for doc in data['docs'] if 'language' in doc]
    languages = list(chain.from_iterable(doc['language'] for doc in data['docs'] if 'language' in doc))
    return languages

