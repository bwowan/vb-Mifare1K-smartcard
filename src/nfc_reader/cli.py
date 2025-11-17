from nfc_reader.do_card import startObserver  # type: ignore[import-not-found]


def main() -> None:
    #Console entry point: waits for card and prints dump.
    startObserver()

