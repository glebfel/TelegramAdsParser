import datetime

import aiohttp as aiohttp
from bs4 import BeautifulSoup

from core import StatsElem, Statistics, CampaignNotExistsError

BASE_URL = 'https://promote.telegram.org/'

BASE_HEADER = {'Accept': '*/*',
               'User-Agent': 'Mozilla/5.0 (compatible; MSIE 10.0; Macintosh; Intel Mac OS X 10_7_3; Trident/6.0)'}


async def parse_header_stats(campaign_id: str) -> dict | None:
    """Get stats from page header (link, status, CPM, views)"""
    # get page html-markup
    async with aiohttp.ClientSession() as session:
        async with session.get(BASE_URL + 'stats/' + campaign_id) as resp:
            page = await resp.text()

    if 'In addition to sending private messages and chatting in ' \
       'private groups, Telegram users can subscribe to' in page:
        raise CampaignNotExistsError(campaign_id)

    page_markup = BeautifulSoup(page, 'lxml')

    # find stats
    stats = page_markup.find_all(class_='pr-review-ad-info')

    # tg link
    tg_link = stats[1].contents[3].a.attrs['href']
    # status
    status = stats[2].contents[3].text.strip()
    # CPM
    cpm = float(stats[3].contents[3].text.replace('€', ''))
    # views
    total_views = stats[4].contents[3].text.replace(',', '')

    return {
        'tg_link': tg_link,
        'status': status,
        'cpm': cpm,
        'total_views': total_views
    }


async def parse_graph_stats(campaign_id: str) -> list[StatsElem] | None:
    # get graph stats in csv
    querystring = {"prefix": f"shared/{campaign_id}", "period": "day"}
    url = BASE_URL + 'csv/'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=querystring) as resp:
            stats_csv = await resp.text()

    # convert csv in python list
    stats_list = [i.split('\t') for i in stats_csv.split('\n')][1:]
    # convert all list's elements to named dicts
    stats_list = [StatsElem(date=datetime.datetime.strptime(i[0], '%d %b %Y'), views=i[1], joined=i[2]) for i in
                  stats_list]

    return stats_list


async def collect_data(campaign_id: str) -> Statistics:

    # collect header stats
    header_stats = await parse_header_stats(campaign_id)

    # collect graph stats
    graph_stats = await parse_graph_stats(campaign_id)

    # calculate other total values (total_joined, total_spent, subscriber_cost)
    total_joined = sum([i.joined for i in graph_stats])
    # cost per day = views * cpm / 1000
    total_spent = round(sum([i.views * header_stats['cpm'] / 1000 for i in graph_stats]), 2)
    # subscriber_cost = total_spent/total_joined
    subscriber_cost = round(total_spent/total_joined, 2)

    return Statistics(**header_stats,
                      total_joined=total_joined,
                      total_spent=total_spent,
                      subscriber_cost=subscriber_cost,
                      graph_stats=graph_stats)
