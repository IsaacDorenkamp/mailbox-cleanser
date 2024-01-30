import argparse

import app


def get_program_options():
    parser = argparse.ArgumentParser(prog="Mailbox Cleanser", description="Tool for cleansing your mailbox of marketing e-mails and other such junk.")
    parser.add_argument('--force-authorize', action="store_true")
    parser.add_argument('--remove', required=False)

    return parser.parse_args()


if __name__ == '__main__':
    try:
        app.main(get_program_options())
    except KeyboardInterrupt:
        print("\nForce quit. Exiting gracefully.")
