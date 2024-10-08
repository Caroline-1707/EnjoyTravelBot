import requests
from typing import List, Any
import json
import os
from dotenv import load_dotenv
from loader import bot

load_dotenv()


def api_request(method, url, headers, params=None, json=None):
    try:
        if params:
            response = requests.request(method=method, url=url, params=params, headers=headers, timeout=10)
        else:
            response = requests.request(method=method, url=url, json=json, headers=headers, timeout=10)
        if response.status_code == requests.codes.ok:
            return response
    except (ConnectionError, ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
        raise ValueError('Ошибка! Отсутствует соединение.')


def city_request(city_name: str) -> List:
    """
    Формирует и обрабатывает запрос города

    :param city_name: город для поиска

    :return: список найденных городов
    """

    url = "https://hotels4.p.rapidapi.com/locations/v3/search"
    querystring = {"q": city_name, "locale": "en_US"}
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPID_API_KEY"),
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }
    try:
        response = json.loads(api_request("GET", url, params=querystring, headers=headers).text)

        if response['sr']:
            cities = list()
            for dest in response['sr']:
                cities.append({'city_name': dest['regionNames']['fullName'],
                               'destination_id': dest['gaiaId'] if 'gaiaId' in dest.keys() else dest['hotelId']
                               })
        else:
            raise PermissionError('К сожалению, город не найден. Попробуем еще раз?')

        return cities

    except (LookupError, TypeError, AttributeError):
        raise ValueError('Возникла непредвиденная ошибка.')


def hotels_request(user_id, chat_id, sort_order, is_reverse=False):
    """
    Обрабатывает запрос отеля. Возвращает словарь, где ключ - название отеля,
    значение - словарь с ключами - [id, адрес, расстояние от центра, цена, общая стоимость, рейтинг, ссылка]
    """
    with bot.retrieve_data(user_id, chat_id) as hotels_data:
        url = "https://hotels4.p.rapidapi.com/properties/v2/list"

        payload = {
            "currency": "RUB",
            "eapid": 1,
            "locale": "en_US",
            "siteId": 300000001,
            "destination": {"regionId": hotels_data['city_id']},
            "checkInDate": {
                "day": hotels_data['check_in'].day,
                "month": hotels_data['check_in'].month,
                "year": hotels_data['check_in'].year
            },
            "checkOutDate": {
                "day": hotels_data['check_out'].day,
                "month": hotels_data['check_out'].month,
                "year": hotels_data['check_out'].year
            },
            "rooms": [
                {
                    "adults": 1
                }
            ],
            "resultsStartingIndex": 0,
            "resultsSize": hotels_data['hotels_count'],
            "sort": sort_order,
            "filters": {"price": {
                "max": hotels_data['price_max'] if 'price_max' in hotels_data.keys() else None,
                "min": hotels_data['price_min'] if 'price_min' in hotels_data.keys() else None
            }}
        }

        headers = {
            "content-type": "application/json",
            "X-RapidAPI-Key": os.getenv("RAPID_API_KEY"),
            "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
        }
        data = dict()
        try:
            response = json.loads(api_request("POST", url, json=payload, headers=headers).text)
            if 'errors' in response.keys():
                raise ValueError
            result = response['data']['propertySearch']['properties']
            if is_reverse:
                result.reverse()
            for hotel in result:
                name = hotel['name']

                price = round(hotel['price']['lead']['amount']) if 'price' in hotel.keys() else None
                total_days = hotels_data['total_days'].days if hotels_data['total_days'].days != 0 else 1
                total_price = round(price * total_days) if isinstance(price, int) else None

                address, photos = pictures_request(hotel_id=hotel['id'])

                data[name] = {
                    'hotel_id': hotel['id'],
                    'address': address,
                    'distance': int(hotel['destinationInfo']['distanceFromDestination']['value']),
                    'total_days': total_days,
                    'price': price,
                    'total_price': total_price,
                    'rating': hotel['reviews']['score'] if 'reviews' in hotel.keys() else 'Нет',
                    'linc': f'https://www.hotels.com/h{hotel["id"]}.Hotel-Information',
                    'photos': photos
                }

            return data

        except (LookupError, TypeError, AttributeError):
            raise ValueError('Возникла непредвиденная ошибка.')
        except ValueError:
            return {}


def pictures_request(hotel_id) -> tuple[Any, list[Any]]:
    """ Формирует и обрабатывает запрос фотографий, возвращает ссылки на фото """
    url = "https://hotels4.p.rapidapi.com/properties/v2/detail"

    payload = {
        "currency": "RUB",
        "eapid": 1,
        "locale": "en_US",
        "siteId": 300000001,
        "propertyId": hotel_id
    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": os.getenv("RAPID_API_KEY"),
        "X-RapidAPI-Host": "hotels4.p.rapidapi.com"
    }

    try:
        response = json.loads(api_request("POST", url, json=payload, headers=headers).text)
        result = response['data']['propertyInfo']
        pictures_list = list()
        for index in result['propertyGallery']['images']:
            base_url = index['image']['url']
            pictures_list.append(base_url)

        address = result['summary']['location']['address']['addressLine']
        return address, pictures_list
    except (LookupError, TypeError, AttributeError):
        raise ValueError('Возникла непредвиденная ошибка.')
