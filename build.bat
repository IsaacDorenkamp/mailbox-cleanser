pyinstaller --noconfirm -w -n "Mailbox Cleanser" --add-data="credentials.json;resources" --add-data="resources/google_icon.png;resources" __main__.py