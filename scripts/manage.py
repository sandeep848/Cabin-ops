"""Provision bookings or rotate crew credentials in the configured CabinOps database."""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.database import init_db, get_connection
from backend.models import PassengerAuth
from backend.security.hashing import hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    booking = commands.add_parser('booking', help='Create or update a passenger booking')
    booking.add_argument('--seat', required=True)
    booking.add_argument('--flight', default='APX-001')
    booking.add_argument('--name', required=True)
    crew = commands.add_parser('crew', help='Create or rotate a crew account')
    crew.add_argument('--username', required=True)
    args = parser.parse_args()
    init_db()
    if args.command == 'booking':
        reference = getpass.getpass('Booking reference (hidden): ').strip().upper()
        payload = PassengerAuth(seat=args.seat, booking_reference=reference)
        with get_connection() as conn:
            conn.execute('INSERT INTO bookings (seat, flight_id, booking_reference, passenger_name) VALUES (?, ?, ?, ?) ON CONFLICT(flight_id, seat) DO UPDATE SET booking_reference=excluded.booking_reference, passenger_name=excluded.passenger_name', (payload.seat, args.flight, payload.booking_reference, args.name))
        print(f'Booking saved for seat {payload.seat} on {args.flight}.')
    else:
        password = getpass.getpass('New crew password (hidden): ')
        if len(password) < 12:
            parser.error('Use a crew password of at least 12 characters.')
        if password != getpass.getpass('Confirm password: '):
            parser.error('Passwords do not match.')
        with get_connection() as conn:
            conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?) ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role', (args.username, hash_password(password), 'crew'))
        print(f'Crew credentials saved for {args.username}. Existing sessions remain valid until expiry or signing-key rotation.')


if __name__ == '__main__':
    main()
