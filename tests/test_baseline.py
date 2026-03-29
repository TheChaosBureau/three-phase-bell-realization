import io
import math

import allure
import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def test_true():
    assert True

def test_attach_sine_wave_to_allure_report():
    x_values = [math.tau * x / 199 for x in range(200)]
    y_values = [np.sin(x) for x in x_values]

    figure = Figure(figsize=(6, 3), dpi=100)
    FigureCanvasAgg(figure)
    axis = figure.subplots()
    axis.plot(x_values, y_values, color="#1f77b4", linewidth=2)
    axis.axhline(0, color="#d9d9d9", linewidth=1)
    axis.set_xlim(0, math.tau)
    axis.set_ylim(-1.1, 1.1)
    axis.set_title("Sine Wave")

    png_buffer = io.BytesIO()
    figure.savefig(png_buffer, format="png")
    png_bytes = png_buffer.getvalue()

    allure.attach(
        png_bytes,
        name="sine-wave",
        attachment_type=allure.attachment_type.PNG,
    )
    assert png_bytes.startswith(b"\x89PNG")
