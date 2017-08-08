#! /usr/bin/env python
# -*- coding: utf-8 -*-

""" Players Module

.. moduleauthor:: Timothy Helton <timothy.j.helton@gmail.com>
"""
import io
import logging
import os.path as osp
import re
import urllib

from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns

from nba_stats.utils import save_fig, size


log_format = ('%(asctime)s  %(levelname)8s  -> %(name)s <- '
              '(line: %(lineno)d) %(message)s\n')
date_format = '%m/%d/%Y %I:%M:%S'
logging.basicConfig(format=log_format, datefmt=date_format,
                    level=logging.INFO)

current_dir = osp.dirname(osp.realpath(__file__))
data_dir = osp.realpath(osp.join(current_dir, '..', 'data'))
players_file = osp.join(data_dir, 'Players.csv')
season_file = osp.join(data_dir, 'Seasons_Stats.csv')


class Statistics:
    """
    Methods and attributes related to NBA player statistics.

    ..note:: Original Player and Season Statistics datasets from \
        `kaggle <https://www.kaggle.com/drgilermo/nba-players-stats>`_ \
        NBA Players stats since 1950 dataset.

    ..note:: See \
    `Glossary <https://www.basketball-reference.com/about/glossary.html>`_ \
    for basketball statistic terms definitions.

    :Attributes:

    - **fame**: *Series* players in the Hall of Fame
    - **players**: *DataFrame* player dataset
    - **players_fame**: *DataFrame* player dataset filtered to only include \
        Hall of Fame members
    - **players_types**: *dict* data types for player dataset
    - **stats**: *DataFrame* season statistics dataset
    - **stats_fame**: *DataFrame* stats dataset filtered to only include \
        Hall of Fame members
    - **stats_types**: *dict* data types for season statistics dataset
    """
    def __init__(self):
        self.fame = None
        self.fame_types = {
            'name': str,
            'category': 'category'
        }

        self.players = None
        self.players_types = {
            'idx': np.int,
            'player': str,                                  # Player
            'height': np.float,                             # height
            'weight': np.float,                             # weight
            'collage': 'category',                          # collage
            'born': str,                                    # born
            'birth_city': str,                              # birth_city
            'birth_state': 'category',                      # birth_state
        }
        self.players_fame = None

        self.stats = None
        self.stats_types = {
            'idx': np.int,
            'season': str,                                  # Year
            'player': str,                                  # Player
            'position': 'category',                         # Pos
            'age': np.float,                                # Age
            'team': 'category',                             # Tm
            'games': np.int,                                # G
            'games_started': np.float,                      # GS
            'minutes_played': np.float,                     # MP
            'efficiency_rating': np.float,                  # PER
            'true_shooting_pct': np.float,                  # TS%
            '3_point_average_attempts': np.float,           # 3PAr
            'ftr': np.float,                                # FTr
            'offensive_rebound_pct': np.float,              # ORB%
            'defensive_rebound_pct': np.float,              # DRB%
            'total_rebound_pct': np.float,                  # TRB%
            'assist_pct': np.float,                         # AST%
            'steal_pct': np.float,                          # STL%
            'block_pct': np.float,                          # BLK%
            'turnovers_pct': np.float,                      # TOV%
            'usage_pct': np.float,                          # USG%
            'blank_1': str,                                 # Blank Line 1
            'offensive_win_shares': np.float,               # OWS
            'defensive_win_shares': np.float,               # DWS
            'win_shares': np.float,                         # WS
            'win_shares_48': np.float,                      # WS/48
            'blank_2': str,                                 # Blanks Line 2
            'offensive_box_plus_minus': np.float,           # OBPM
            'defensive_box_plus_minus': np.float,           # DBPM
            'box_plus_minus': np.float,                     # BPM
            'value_over_replacement_player': np.float,      # VORP
            'field_goals': np.int,                          # FG
            'field_goal_attempts': np.int,                  # FGA
            'field_goal_pct': np.float,                     # FG%
            '3_pointers': np.float,                         # 3P
            '3_painters_attempts': np.float,                # 3PA
            '3_pointers_pct': np.float,                     # 3P%
            '2_pointers': np.int,                           # 2P
            '2_pointers_attempts': np.int,                  # 2PA
            '2_pointers_pct': np.float,                     # 2P%
            'effective_field_goal_pct': np.float,           # eFG%
            'free_throws': np.int,                          # FT
            'free_throw_attempts': np.int,                  # FTA
            'free_throw_pct': np.float,                     # FT%
            'offensive_rebounds': np.float,                 # ORB
            'defensive_rebounds': np.float,                 # DRB
            'total_rebounds': np.float,                     # TRB
            'assists': np.float,                            # AST
            'steals': np.float,                             # STL
            'blocks': np.float,                             # BLK
            'turnovers': np.float,                          # TOV
            'fouls': np.int,                                # PF
            'points': np.int,                               # PTS
        }
        self.stats_fame = None

        try:
            self.fame = pd.read_csv('https://timothyhelton.github.io/'
                                    'assets/data/NBA_Hall_of_Fame.csv',
                                    dtype=self.fame_types,
                                    header=None,
                                    index_col=0,
                                    names=self.fame_types.keys(),
                                    skiprows=1,
                                    )
            logging.info('NBA Hall of Fame Players from '
                         'https://timothyhelton.github.io')
        except urllib.error.HTTPError:
            self.scrape_hall_of_fame()
        # Dan Issel's name is misspelled on the NBA Hall of Fame website
        self.fame.name = self.fame.name.str.replace('Dan Issell', 'Dan Issel')

        self.load_data()

    def __repr__(self):
        return 'Statistics()'

    def load_data(self):
        """
        Load the player and stats datasets.
        """
        def blank_filter(text):
            """
            Remove blank line entries.

            :param str text: original text
            :return: text with blank entries removed
            :rtype: str
            """
            return re.sub(r'^\d+,+$', '', text, flags=re.MULTILINE)

        def year_parser(year):
            """
            Format year string to be ISO 8601 string.
            :param year: year
            :return: year in ISO 8601 format
            :rtype: str
            """
            return [f'{x}-01-01' for x in year]

        self.players = (pd.read_csv(players_file,
                                    date_parser=year_parser,
                                    dtype=self.players_types,
                                    header=None,
                                    index_col=5,
                                    names=self.players_types.keys(),
                                    parse_dates=[5],
                                    skiprows=1,
                                    )
                        .drop('idx', axis=1)
                        .dropna(how='all'))
        self.players.player = self.players.player.str.replace('*', '')
        logging.debug('Players Dataset Loaded')

        with open(season_file, 'r') as f:
            season_text = f.read()
            filtered_text = blank_filter(season_text)
            logging.info('Season Stats Dataset cleaned')

        self.stats = (pd.read_csv(io.StringIO(filtered_text),
                                  date_parser=year_parser,
                                  dtype=self.stats_types,
                                  header=None,
                                  index_col=1,
                                  names=self.stats_types.keys(),
                                  parse_dates=[1],
                                  skiprows=1,
                                  )
                      .drop(['blank_1', 'blank_2', 'idx'], axis=1))
        self.stats.player = self.stats.player.str.replace('*', '')
        logging.debug('Season Stats Dataset Loaded')

        filter_players = self.fame.query('category == "Player"').name

        self.players_fame = self.players[(self.players.player
                                          .isin(filter_players))]

        self.stats_fame = self.stats[(self.stats.player
                                      .isin(filter_players))]

    def scrape_hall_of_fame(self):
        """
        Scrape all the NBA Hall of Fame inductees.

        ..note:: NBA Hall of Fame Inductees scraped from www.nba.com website.
        """
        url = ('http://www.nba.com/history/naismith-memorial-basketball-hall'
               '-of-fame-inductees/')
        request = requests.get(url)
        soup = BeautifulSoup(request.text, 'lxml')
        section = soup.find('section', id='nbaArticleContent')
        tags = section.find_all('p')
        members = re.findall(r'<p>\s<b>(.+?)</b>(.+?)</p>', str(tags))
        remove_tags = [(x[0], re.sub(r'</?\w>', '', x[1]))
                       for x in members[1:]]
        remove_spaces = [(x[0], re.sub(r'\s', '', x[1])) for x in remove_tags]
        remove_commas = [(x[0], re.sub(r',', '', x[1])) for x in remove_spaces]
        self.fame = pd.DataFrame(remove_commas, columns=['name', 'category'])
        logging.info('NBA Hall of Fame Players Scraped from www.nba.com')

    def missing_hall_of_fame(self):
        """
        Players in the Hall of Fame without entries in the datasets.

        :return: names of players not found in the Players and Season Stats \
            datasets
        :rtype: DataFrame
        """
        no_players = (self.fame[~self.fame.isin((self.players_fame
                                                 .player
                                                 .tolist()))]
                      .dropna()
                      .query('category == "Player"')
                      .name)
        logging.debug('DIFF players Hall of Fame to Players Dataset complete')
        no_stats = (self.fame[~self.fame.isin(self.stats.player.unique())]
                    .dropna()
                    .query('category == "Player"')
                    .name)
        logging.debug('DIFF players Hall of Fame to Stats Dataset complete')
        return (pd.concat([no_players, no_stats], axis=1, join='outer',
                          ignore_index=True)
                .rename(columns={n: name for n, name
                                 in enumerate(('player_dataset',
                                               'stats_dataset'))})
                .reset_index(drop=True))

    def hof_category_plot(self, save=False):
        """
        Horizontal Bar chart of Hall of Fame categories.

        :param bool save: if True the figure will be saved
        """
        plt.figure('Hall of Fame Categories', figsize=(12, 3),
                   facecolor='white', edgecolor=None)
        rows, cols = (1, 1)
        ax0 = plt.subplot2grid((rows, cols), (0, 0))

        categories = (self.fame
                      .groupby('category')
                      .count()
                      .sort_values(by='name'))

        categories.plot(kind='barh', alpha=0.5, color=['gray'],
                        edgecolor='black', legend=None, width=0.7, ax=ax0)

        emphasis = categories.index.get_loc('Player')
        ax0.patches[emphasis].set_facecolor('C0')
        ax0.patches[emphasis].set_alpha(0.7)
        width = ax0.patches[emphasis].get_width()
        height = ax0.patches[emphasis].get_height()
        ax0.text(x=width - 2,
                 y=ax0.patches[emphasis].get_y() + height / 2 - 0.15,
                 s=f'{width:.0f}',
                 fontsize=size['label'],
                 ha='right')

        ax0.set_title('Naismith Memorial Basketball Hall of Fame Categories',
                      fontsize=size['title'])
        ax0.set_ylabel('')

        ax0.set_xticklabels('')
        ax0.xaxis.set_ticks_position('none')
        ax0.yaxis.set_ticks_position('none')
        ax0.set_yticklabels(ax0.yaxis.get_majorticklabels(),
                            fontsize=size['legend'])
        ax0.spines['top'].set_visible(False)
        ax0.spines['right'].set_visible(False)
        ax0.spines['bottom'].set_visible(False)
        ax0.spines['left'].set_visible(False)

        save_fig('hof_category', save)
