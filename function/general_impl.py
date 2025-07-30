import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

matplotlib.use('Agg')

# 현재 파일 기준으로 상위 폴더의 font/malgun.ttf 경로 지정
current_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.abspath(os.path.join(current_dir, '..', 'font', 'malgun.ttf'))

if not os.path.exists(font_path):
    raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_path}")

# 폰트 적용
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)


def function_generate_bargraph(data, title=None, x_label=None, y_label=None, save_path=None):
    if not isinstance(data, dict):
        raise ValueError("data는 딕셔너리 형식이어야 합니다.")

    # 디폴트 제목/축 이름 처리
    title = title or "Bar Graph"
    x_label = x_label or "X"
    y_label = y_label or "Y"

    # X, Y 추출
    x = list(data.keys())
    y = list(data.values())

    plt.figure(figsize=(10, 5))
    plt.bar(x, y, color='skyblue')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(axis='y')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # 저장 경로 처리
    if save_path is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(base_dir, exist_ok=True)
        save_path = os.path.join(base_dir, "bar_graph.png")

    plt.savefig(save_path)
    plt.close()

    return save_path


def function_generate_linegraph(data, title=None, x_label=None, y_label=None, save_path=None):
    if not isinstance(data, dict):
        raise ValueError("data는 딕셔너리 형식이어야 합니다.")

    title = title or "Line Graph"
    x_label = x_label or "X"
    y_label = y_label or "Y"

    x = list(data.keys())
    y = list(data.values())

    plt.figure(figsize=(10, 5))
    plt.plot(x, y, marker='o', color='orange')
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    if save_path is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(base_dir, exist_ok=True)
        save_path = os.path.join(base_dir, "line_graph.png")

    plt.savefig(save_path)
    plt.close()

    return save_path


def function_generate_piechart(data, title=None, x_label=None, y_label=None, save_path=None):
    if not isinstance(data, dict):
        raise ValueError("data는 딕셔너리 형식이어야 합니다.")

    title = title or "Pie Chart"

    labels = list(data.keys())
    values = list(data.values())

    plt.figure(figsize=(7, 7))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
    plt.title(title)
    plt.tight_layout()

    if save_path is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(base_dir, exist_ok=True)
        save_path = os.path.join(base_dir, "pie_chart.png")

    plt.savefig(save_path)
    plt.close()

    return save_path
