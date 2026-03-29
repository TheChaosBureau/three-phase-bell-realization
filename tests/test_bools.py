def test_true():
    assert True

@pytest.xfail
def test_xfail():
    assert False