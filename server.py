#!/usr/bin/env python3
"""Малък HTTP сървър върху сокети. Сервира две HTML страници.

Сървърът слуша на един адрес и един порт: 127.0.0.1:8080.
Браузърът при всяка заявка отваря своя временен порт. Той не се
показва в лога, защото проектът демонстрира един сървърен порт.
"""

import socket
from pathlib import Path

# Адресът 127.0.0.1 е само тази машина (localhost).
# Порт 8080 е единственият порт, на който сървърът приема връзки.
HOST = "127.0.0.1"
PORT = 8080

# Папката pages стои до този файл, независимо от текущата директория.
PAGES = Path(__file__).resolve().parent / "pages"

# Път от заявката -> файл в pages/. И двата записа сочат към един и същ файл,
# за да работят и краткият адрес, и адресът с разширение .html.
ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/about": "about.html",
    "/about.html": "about.html",
}


def http_response(status: str, body: bytes, content_type: str) -> bytes:
    """Сглобява пълен HTTP отговор: заглавна част и тяло.

    Редовете в заглавната част завършват с \\r\\n. Празен ред разделя
    заглавната част от тялото. Content-Length казва на браузъра колко
    байта тяло да прочете. Connection: close затваря връзката след отговора.
    """
    header = (
        f"HTTP/1.1 {status}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    return header.encode("utf-8") + body


def handle_request(raw: bytes) -> bytes:
    """Чете първия ред на заявката и връща готовия HTTP отговор.

    Първият ред изглежда така: GET /about HTTP/1.1
    От него се взимат методът и пътят. Останалите заглавни редове
    на заявката не са нужни за тези две страници.
    """
    try:
        # Заявката идва като байтове. Първият ред е до първото \r\n.
        request_line = raw.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
        method, path, *_ = request_line.split(" ")
    except ValueError:
        # Редът няма очакваните полета (метод, път, версия).
        return http_response(
            "400 Bad Request",
            b"<h1>400 Bad Request</h1>",
            "text/html; charset=utf-8",
        )

    # Махаме query string (?a=1), за да сравняваме само пътя.
    path = path.split("?", 1)[0]
    if method != "GET":
        return http_response(
            "405 Method Not Allowed",
            b"<h1>405 Method Not Allowed</h1>",
            "text/html; charset=utf-8",
        )

    filename = ROUTES.get(path)
    if filename is None:
        return http_response(
            "404 Not Found",
            b"<h1>404 Not Found</h1>",
            "text/html; charset=utf-8",
        )

    page = PAGES / filename
    if not page.is_file():
        return http_response(
            "404 Not Found",
            b"<h1>404 Not Found</h1>",
            "text/html; charset=utf-8",
        )

    return http_response("200 OK", page.read_bytes(), "text/html; charset=utf-8")


def serve() -> None:
    """Отваря TCP сокет, слуша на един порт и обслужва заявките една по една."""
    # AF_INET = IPv4. SOCK_STREAM = TCP, защото HTTP върви върху TCP.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        # Позволява повторно стартиране веднага след спиране,
        # без грешка „Address already in use“ от предишния процес.
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Закача сокета към един адрес и един порт.
        server.bind((HOST, PORT))
        # Опашка от до 5 чакащи връзки, докато текущата се обработва.
        server.listen(5)
        print(f"Сървърът слуша на http://{HOST}:{PORT}")
        print("Страници: /  и  /about")
        print("Спри с Ctrl+C")

        while True:
            # accept() блокира, докато браузър се свърже.
            # Връща нов сокет само за тази връзка. Сървърният сокет
            # остава на порт 8080 и продължава да слуша.
            conn, _addr = server.accept()
            with conn:
                # Четем, докато стигнем празния ред, който затваря заглавната част.
                raw = b""
                while b"\r\n\r\n" not in raw:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    raw += chunk
                if not raw:
                    continue
                request_line = raw.split(b"\r\n", 1)[0].decode(errors="replace")
                # В лога е портът на сървъра, не временният порт на браузъра.
                print(f"{HOST}:{PORT}  {request_line}")
                conn.sendall(handle_request(raw))


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        # Ctrl+C вдига KeyboardInterrupt. Сървърът спира без traceback.
        print("\nСпрян.")
