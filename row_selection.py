import re
from typing import List, Optional


ALL_ROW_TOKENS = {"*", "all", "todas", "todos"}
MAX_SELECTED_ROWS = 10000


def parse_row_selection(
    selection: object,
    total_rows: Optional[int] = None,
    max_selected: int = MAX_SELECTED_ROWS,
) -> Optional[List[int]]:
    """Return unique 1-based row numbers, or None when all rows are selected."""
    text = str(selection or "").strip().lower()
    if not text or text in ALL_ROW_TOKENS:
        return None

    tokens = [token for token in re.split(r"[,;\s]+", text) if token]
    selected = set()
    for token in tokens:
        match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", token)
        if not match:
            raise ValueError(
                f"Selecao de linhas invalida: {token!r}. Use exemplos como 2,5,8-12 ou todos."
            )

        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < 1:
            raise ValueError("Os numeros das linhas precisam ser maiores ou iguais a 1.")
        if end < start:
            raise ValueError(f"Intervalo de linhas invertido: {start}-{end}.")
        if total_rows is not None and end > total_rows:
            raise ValueError(
                f"Linha {end} fora do intervalo: a planilha tem {total_rows} linhas."
            )
        if end - start + 1 > max_selected:
            raise ValueError(f"A selecao pode conter no maximo {max_selected} linhas.")

        selected.update(range(start, end + 1))
        if len(selected) > max_selected:
            raise ValueError(f"A selecao pode conter no maximo {max_selected} linhas.")

    return sorted(selected)
