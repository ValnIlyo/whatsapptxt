import io
import re
import math
from io import TextIOWrapper
from django.shortcuts import render
from django.http import FileResponse


def index(request):
    return render(request, "index.html")


def parser(request):
    if request.method == "POST" and request.FILES["txt"] != 0:
        primary = request.POST["primary"]
        secondary = request.POST["secondary"]
        strings = TextIOWrapper(
            request.FILES["txt"], encoding="utf-8").readlines()
    result = parsing(strings, primary, secondary)
    PercentagePrimary = round((result["you"]) / result["sum"] * 100)
    PercentageSecondary = round(
        (result["sum"] - result["you"]) / result["sum"] * 100)
    if PercentagePrimary > PercentageSecondary:
        big = PercentagePrimary
        small = PercentageSecondary
    else:
        big = PercentageSecondary
        small = PercentagePrimary
    params = {
        "chat": result["chat"],
        "primary": primary,
        "second": secondary,
        "sum": result["sum"],
        "you": result["you"],
        "contact": result["contact"],
        "PercentagePrimary": small,
        "PercentageSecondary": big,
        "years": result["years"],
        "months": result["months"],
    }
    request.session["params"] = params
    return render(request, "parsed.html", params)


def download(request):
    params = request.session["params"]
    response = render(request, "whatsapp.html", params)
    html = io.BytesIO(response.content)
    return FileResponse(
        html,
        as_attachment=True,
        filename="WhatsApp chat with " + params["second"] + ".html",
    )


def parsing(strings: list, primary: str, secondary: str):
    PatternInfo = FindPattern(strings, primary, secondary)
    merged = MessageMerger(strings, PatternInfo["pattern"])
    extracted = extractor(
        merged, PatternInfo["pattern"], PatternInfo["PatternIndex"])
    years = math.floor(extracted["NoOfMonths"] / 12)
    months = extracted["NoOfMonths"] % 12
    sum = 0
    you = 0
    contact = 0
    for text in extracted["texts"]:

        text["message"] = re.sub(
            "<",
            "&lt",
            text["message"],
        )
        text["message"] = re.sub(
            ">",
            "&gt",
            text["message"],
        )
        text["message"] = re.sub(
            "&ltMedia omitted&gt", "<tt>Cannot display media</tt>", text["message"]
        )
        text["message"] = re.sub(
            "You deleted this message\\n",
            "<tt>This message was deleted</tt>",
            text["message"],
        )
        text["message"] = re.sub(
            "This message was deleted\\n",
            "<tt>This message was deleted</tt>",
            text["message"],
        )
        sum += 1
        if any(writer == text["writer"] for writer in [primary, primary + ":same"]):
            you += 1
        if any(writer == text["writer"] for writer in [secondary, secondary + ":same"]):
            contact += 1
    result = {
        "chat": extracted["texts"],
        "sum": sum,
        "you": you,
        "contact": contact,
        "years": years,
        "months": months,
    }
    return result


def extractor(merged: list, pattern: str, PatternIndex: str):
    texts = []
    NoOfMonths = 0
    last_date = str()
    last_year = str()
    last_month = str()
    last_writer = str()
    for string in merged:
        match = re.match(pattern, string)
        if match:
            Info = {}
            calender = Calender(match)
            if (last_month != calender["month"]) or (
                last_month == calender["month"] and last_year != calender["year"]
            ):
                NoOfMonths += 1
                last_month = calender["month"]
                last_year = calender["year"]
            if calender["date"] != last_date:
                last_date = calender["date"]
                Info["date"] = calender["date"]
            if PatternIndex == 0:
                time = match.group(6) + ":" + match.group(7)
                current_writer = match.group(8)
            else:
                time = match.group(6) + ":" + \
                    match.group(7) + " " + match.group(8)
                current_writer = match.group(9)
            Info["time"] = time
            if current_writer != last_writer:
                last_writer = current_writer
                Info["writer"] = current_writer
            else:
                Info["writer"] = current_writer + ":same"
            message = re.sub(pattern, "", string)
            Info["message"] = message
            texts.append(Info)
    extracted = {"NoOfMonths": NoOfMonths, "texts": texts}
    return extracted


def Calender(match: re.match):
    months = [
        "January",
        "Februrary",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    month = match.group(1)
    month = months[int(month) - 1]
    year = match.group(5)
    date = month + " " + match.group(3) + ", 20" + year
    calender = {"date": date, "month": month, "year": year}
    return calender


def MessageMerger(strings: list, pattern: str):
    merged = []
    for string in strings:
        current_index = strings.index(string)
        match = re.match(pattern, string)
        if match:
            merged.append(strings[current_index])
        else:
            if merged != []:
                strings[current_index] = (
                    strings[current_index - 1] + "" + strings[current_index]
                )
                merged.pop()
                merged.append(strings[current_index])
    return merged


def FindPattern(strings: list, primary: str, secondary: str):
    patterns = [
        "([0-9]+)(/)([0-9]+)(/)([0-9][0-9]), ([0-9]+):([0-9]+)",
        "([0-9]+)(/)([0-9]+)(/)([0-9][0-9]), ([0-9]+):([0-9]+) (AM|PM)",
    ]
    for TimePattern in patterns:
        TestPattern = r"^" + TimePattern + \
            " - (" + primary + "|" + secondary + "):"
        for string in strings[0:6]:
            match = re.match(TestPattern, string)
            if match:
                pattern = TestPattern
                PatternIndex = patterns.index(TimePattern)
                break
    PatternInfo = {"pattern": pattern, "PatternIndex": PatternIndex}
    return PatternInfo
