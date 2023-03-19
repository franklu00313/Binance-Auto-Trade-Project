import requests

def lineNotifyMessage(token: str, msg: str, notify_flag: bool = True, imgFullUrl: str = None, imgThumbUrl: str = None) -> list[int]:
    """
      Send message(maybe with png) using Line Notify Service.

      Return response status code.
    """
    headers = {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {'message': msg, "imageFullsize": imgFullUrl,
               'imageThumbnail': imgThumbUrl, 'notificationDisabled': not notify_flag}

    r = requests.post("https://notify-api.line.me/api/notify",
                      headers=headers, params=payload)
    return r.status_code