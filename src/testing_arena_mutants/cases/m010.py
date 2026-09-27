"""Weather-data utilities used by the mutation test arena."""


def parse_time(time_text):
    """Convert a time in HH:MM format to minutes since midnight."""
    parts = time_text.split(":")

    if len(parts) != 2:
        raise ValueError("Time must have HH:MM format.")

    hour_text, minute_text = parts

    if not hour_text.isdigit() or not minute_text.isdigit():
        raise ValueError("Hour and minute must be numeric.")

    hour = int(hour_text)
    minute = int(minute_text)

    if hour < 0 or hour > 23:
        raise ValueError("Hour must be between 0 and 23.")

    if minute < 0 or minute > 59:
        raise ValueError("Minute must be between 0 and 59.")

    return hour * 60 + minute


def parse_measurement(line):
    """Parse one weather measurement in city;HH:MM;temperature format."""
    if not isinstance(line, str):
        raise ValueError("Measurement must be a string.")

    parts = line.split(";")

    if len(parts) != 3:
        raise ValueError("Expected exactly three fields.")

    city = parts[0].strip()
    time_text = parts[1].strip()
    temperature_text = parts[2].strip()

    if city == "":
        raise ValueError("City must not be empty.")

    time = parse_time(time_text)

    try:
        temperature = float(temperature_text)
    except ValueError:
        raise ValueError("Temperature must be numeric.")

    return city, time, temperature


def filter_by_temperature(measurements, lower, upper):
    """Return measurements inside the inclusive temperature range."""
    if lower > upper:
        raise ValueError("lower must not be greater than upper.")

    result = []

    for measurement in measurements:
        temperature = measurement[2]

        if lower <= temperature <= upper:
            result.append(measurement)

    return result


def average_temperature(measurements, city):
    """Return the average temperature measured in a city."""
    temperatures = []

    for measurement in measurements:
        if measurement[0].lower() == city.lower():
            temperatures.append(measurement[2])

    if len(temperatures) == 0:
        raise ValueError("No measurements found for city.")

    return sum(temperatures) / len(temperatures)


def hottest_measurement(measurements):
    """Return the hottest measurement; ties are resolved by earliest time."""
    if len(measurements) == 0:
        raise ValueError("No measurements available.")

    hottest = measurements[0]

    for measurement in measurements[1:]:
        temperature = measurement[2]
        hottest_temperature = hottest[2]

        if temperature > hottest_temperature:
            hottest = measurement

        elif temperature == hottest_temperature:
            if measurement[1] < hottest[1]:
                hottest = measurement

    return hottest
