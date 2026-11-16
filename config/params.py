"""쿼리 파라미터 값 해석."""

# PostgreSQL integer(기본 id 필드)의 최댓값
MAX_ID = 2_147_483_647


def parse_id(value: str | None) -> int | None:
    """ASCII 숫자로 된 1 이상 MAX_ID 이하의 id만 int로 돌려준다. 나머지는 None.

    str.isdigit()은 「²」 같은 유니코드 숫자도 통과시켜 int()나 ORM에서 500이 나므로 쓰지 않는다.
    """
    if value is None or not value.isascii() or not value.isdigit():
        return None
    number = int(value)
    return number if 1 <= number <= MAX_ID else None
