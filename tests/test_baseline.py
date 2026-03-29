import allure
import pytest
import numpy as np

import matplotlib.pyplot as plt

plt.use("Agg")

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def test_true():
    assert True

@pytest.mark.xfail
def test_xfail():
    assert False


def test_attach_sine_wave_to_allure_report():
    x_values = [np.tau * x / 199 for x in range(200)]
    y_values = [np.sin(x) for x in x_values]

    plt.figure = Figure(figsize=(6, 3), dpi=100)
    plt.FigureCanvasAgg(figure)
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
