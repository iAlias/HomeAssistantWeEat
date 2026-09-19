from custom_components.we_eat.const import DEFAULT_MEAL_TIMES, DOMAIN, MEALS


def test_meals_follow_the_day_and_have_a_time():
    assert DOMAIN == "we_eat"
    assert MEALS == ("colazione", "spuntino", "pranzo", "merenda", "cena")
    assert set(DEFAULT_MEAL_TIMES) == set(MEALS)
    times = [DEFAULT_MEAL_TIMES[m] for m in MEALS]
    assert times == sorted(times)
