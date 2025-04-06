from playwright.sync_api import sync_playwright # type: ignore
import os
import json
from func import select_date, edit_page, nach_page, find_child, new_contract, new_dogovor
from exel import df_load, df_filter, df_replace, df_save, df_find
import sys
import traceback
import math

def exel_save(orig_df, sheet, records):
    if records:
        new_df = df_replace(orig_df, records)
        df_save(new_df, sheet)
    else:
        print("Массив для сохранения в таблице пустой")

df, orig_df, sheet = df_load()
records = df_filter(df, 'январь')

records = [entry for entry in records if entry['фио '] == 'Гапонов Егор'] #DEBUG# 

if records:
    # Пример вывода одного элемента
    for i, record in enumerate(records): 
        print(f"\nПоиск заявлениий ребенка {record['фио ']} [{i+1}/{len(records)}]")

        record['номер договора'] = '1/2025'
        exel_save(orig_df, sheet, records[i])
        #exel_save(orig_df, sheet, records[i]) #Сохраняем номер контракта