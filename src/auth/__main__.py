"""Creation des comptes : python -m src.auth create-user --name "Alice" [--admin]"""

import argparse
import asyncio

from src.auth.service import create_user
from src.database import engine, session_factory


async def create(name, is_admin):
    async with session_factory() as session:
        user, api_key = await create_user(session, name, is_admin)
    await engine.dispose()
    role = "administrateur" if is_admin else "utilisateur"
    print(f"Compte {role} cree : {user.name} (id {user.id})")
    print(f"Cle d'API (affichee une seule fois, a transmettre a la personne) :\n{api_key}")


def main():
    parser = argparse.ArgumentParser(prog="python -m src.auth")
    commands = parser.add_subparsers(dest="command", required=True)
    create_parser = commands.add_parser("create-user", help="creer un compte et sa cle d'API")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--admin", action="store_true", help="donner les droits administrateur")
    args = parser.parse_args()
    asyncio.run(create(args.name, args.admin))


if __name__ == "__main__":
    main()
