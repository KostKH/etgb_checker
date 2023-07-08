import logging
import sqlite3
from dataclasses import asdict

import clickhouse_driver

import settings
from core_layer.models import Queries, Results
from helpers.errors_etgb import SaveResultsToDbError


class QueryDb():
    """Класс для базы реквестов"""
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = sqlite3.connect(settings.get_query_db_params())
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, exc_trace):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


class ResultsDb():
    """Класс для базы результатов"""
    def __init__(self):
        self.conn = None
        self.cursor = None

    def __enter__(self):
        self.conn = clickhouse_driver.connect(
            **settings.get_results_db_params()
        )
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, exc_trace):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()


class QueryRepository():
    """Класс репозитория запросов. Содержит методы для сохранения
    и извлечения данных в / из базы запросов. """
    def __init__(self) -> None:
        self.db = QueryDb()

    def create_table(self) -> None:
        with self.db as cur:
            cur.execute('''
                CREATE TABLE queries
                        (id TEXT PRIMARY KEY,
                        status_code INTEGER NOT NULL,
                        status_text TEXT NOT NULL,
                        ozone_response_code INTEGER NOT NULL,
                        etgb_found_total INTEGER NOT NULL,
                        etgb_saved_new INTEGER NOT NULL);''')

    def add(self, data: Queries) -> None:
        """Метод для добавления запроса в базу"""
        existing_item = self.get(data.id)
        if existing_item:
            with self.db as cur:
                cur.execute(
                    '''
                    UPDATE queries
                    SET status_code = ?,
                        status_text = ?,
                        ozone_response_code = ?,
                        etgb_found_total = ?,
                        etgb_saved_new = ?
                    WHERE id = ?;
                    ''',
                    (data.status_code, data.status_text,
                     data.ozone_response_code, data.etgb_found_total,
                     data.etgb_saved_new, data.id))
        else:
            with self.db as cur:
                cur.execute(
                    '''
                    INSERT INTO queries
                        (id, status_code, status_text, ozone_response_code,
                         etgb_found_total, etgb_saved_new)
                    VALUES (?, ?, ?, ?, ?, ?);
                    ''',
                    (data.id, data.status_code, data.status_text,
                     data.ozone_response_code, data.etgb_found_total,
                     data.etgb_saved_new))

    def get(self, id):
        """Метод для получения данных запроса по его id"""
        with self.db as cur:
            cur.execute(
                '''
                SELECT id, status_code, status_text, ozone_response_code,
                    etgb_found_total, etgb_saved_new
                FROM queries
                WHERE id = ?
                ''',
                (id,))
            result = cur.fetchone()
        if not result:
            return None
        return Queries(*result)


class ResultsRepository():
    """Класс репозитория результатов от Озона. Содержит методы для
    сохранения и извлечения данных в / из базы запросов."""

    def __init__(self):
        self.db = ResultsDb()

    def create_table(self):
        """Метод для первичного создания таблиц."""
        with self.db as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS results
                    (posting_number String NOT NULL,
                    etgb_number String NOT NULL,
                    etgb_date Date NOT NULL,
                    etgb_url String NOT NULL)
                ENGINE MergeTree
                ORDER BY etgb_date;''')

    def add(self, data: list[Results]) -> int:
        """Метод добавляет записи в таблицу результатов. Перед добавлением
        Из базы запрашиваются записи за прошедшие N + 2 дня (N определяется
        настройками). Полностью совпадающие данные отсекаются, сохраняются
        только новые записи."""
        try:
            existing_items = self.get_delta_plus_2_days()
            new_entries = [asdict(item) for item in data
                           if item not in existing_items]

            if new_entries:
                with self.db as cur:
                    cur.executemany(
                        '''
                        INSERT INTO results
                            (posting_number, etgb_number, etgb_date, etgb_url)
                        VALUES
                        ''',
                        new_entries)
            return len(new_entries)
        except Exception as e:
            logging.exception(e)
            raise SaveResultsToDbError(e)

    def get_delta_plus_2_days(self) -> set:
        """Метод возвращает записи с декларациями за последние
        N + 2 дня (N определяется настройками)."""
        delta = settings.DELTA_DAYS + 2
        with self.db as cur:
            cur.execute(
                '''
                SELECT posting_number, etgb_number, etgb_date,
                    etgb_url
                FROM results
                WHERE etgb_date > (today() - %(delta)s)
                ''',
                {'delta': delta})
            results = cur.fetchall()
        if not results:
            return set()
        model_results = set()
        for result in results:
            model_results.add(Results(*result))
        return model_results
