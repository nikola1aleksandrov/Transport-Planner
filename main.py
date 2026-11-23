"""Задание 3 по „Софтуерни шаблони“ — избор на подходящ транспорт.

Демонстрирани шаблони:
- Factory: TransportFactory.create()
- Strategy: SelectionStrategy и трите конкретни стратегии
- Facade: TransportPlannerFacade.analyze()

Стартиране: python main.py (отваря Tkinter GUI)
Тестове: python -m unittest discover -s tests -v
Не са необходими външни библиотеки; Tkinter е част от стандартния Python за Windows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isfinite
from typing import Optional


# ----------------------- МОДЕЛИ НА ДАННИ -----------------------

@dataclass(frozen=True)
class Route:
    """Характеристики на маршрута, зададени от потребителя."""

    distance_km: float
    has_public_transport: bool
    has_bike_lanes: bool
    car_access: bool
    fuel_price_eur_per_liter: float = 1.55
    hilly: bool = False

    def __post_init__(self) -> None:
        if not isfinite(self.distance_km) or self.distance_km <= 0:
            raise ValueError("Дистанцията трябва да бъде положително число.")
        if not isfinite(self.fuel_price_eur_per_liter) or self.fuel_price_eur_per_liter <= 0:
            raise ValueError("Цената на горивото трябва да бъде положително число.")


@dataclass(frozen=True)
class TransportResult:
    """Резултат за една форма на транспорт."""

    code: str
    name: str
    possible: bool
    duration_min: Optional[float] = None
    fuel_cost_eur: Optional[float] = None
    total_cost_eur: Optional[float] = None
    reason: str = ""


# ----------------------- ТРАНСПОРТНИ СРЕДСТВА -----------------------

class Transport(ABC):
    """Общ интерфейс на всички видове транспорт."""

    code: str
    name: str

    @abstractmethod
    def evaluate(self, route: Route) -> TransportResult:
        """Проверява маршрута и изчислява времето/разходите."""

    def unavailable(self, reason: str) -> TransportResult:
        return TransportResult(self.code, self.name, False, reason=reason)

    def available(
        self, duration_min: float, fuel_cost_eur: float, total_cost_eur: float
    ) -> TransportResult:
        return TransportResult(
            self.code,
            self.name,
            True,
            round(duration_min, 2),
            round(fuel_cost_eur, 2),
            round(total_cost_eur, 2),
            "Маршрутът е възможен.",
        )


class WalkingTransport(Transport):
    code = "walk"
    name = "Пеша"
    MAX_DISTANCE_KM = 30.0

    def evaluate(self, route: Route) -> TransportResult:
        if route.distance_km > self.MAX_DISTANCE_KM:
            return self.unavailable("Маршрутът е над приетия лимит за ходене: 30 км.")
        speed = 4.0 if route.hilly else 5.0
        return self.available(route.distance_km / speed * 60, 0.0, 0.0)


class BicycleTransport(Transport):
    code = "bike"
    name = "Велосипед"
    MAX_DISTANCE_KM = 70.0

    def evaluate(self, route: Route) -> TransportResult:
        if not route.has_bike_lanes:
            return self.unavailable("По избрания маршрут няма велоалеи.")
        if route.distance_km > self.MAX_DISTANCE_KM:
            return self.unavailable("Маршрутът е над приетия лимит за колело: 70 км.")
        speed = 12.0 if route.hilly else 15.0
        return self.available(route.distance_km / speed * 60, 0.0, 0.0)


class CarTransport(Transport):
    code = "car"
    name = "Автомобил"
    CONSUMPTION_L_PER_100KM = 6.5
    PARKING_MIN = 5.0

    def evaluate(self, route: Route) -> TransportResult:
        if not route.car_access:
            return self.unavailable("Маршрутът не допуска движение с автомобил.")
        speed = 35.0 if route.hilly else 45.0
        duration = route.distance_km / speed * 60 + self.PARKING_MIN
        fuel_cost = (
            route.distance_km
            * self.CONSUMPTION_L_PER_100KM
            / 100
            * route.fuel_price_eur_per_liter
        )
        return self.available(duration, fuel_cost, fuel_cost)


class BusTransport(Transport):
    code = "bus"
    name = "Градски транспорт"
    WAITING_MIN = 8.0
    TICKET_EUR = 1.50
    MAX_DISTANCE_KM = 40.0

    def evaluate(self, route: Route) -> TransportResult:
        if not route.has_public_transport:
            return self.unavailable("Няма градски транспорт по маршрута.")
        if route.distance_km > self.MAX_DISTANCE_KM:
            return self.unavailable("Маршрутът е над приетия градски обхват: 40 км.")
        speed = 20.0 if route.hilly else 25.0
        duration = route.distance_km / speed * 60 + self.WAITING_MIN
        # Пътникът не плаща лично горивото, но плаща билет.
        return self.available(duration, 0.0, self.TICKET_EUR)


# ----------------------- FACTORY PATTERN -----------------------

class TransportFactory:
    """Създава конкретен транспорт по неговия код."""

    @staticmethod
    def create(code: str) -> Transport:
        transport_classes = {
            "walk": WalkingTransport,
            "bike": BicycleTransport,
            "car": CarTransport,
            "bus": BusTransport,
        }
        transport_class = transport_classes.get(code)
        if transport_class is None:
            raise ValueError(f"Непознат транспорт: {code}")
        return transport_class()


# ----------------------- STRATEGY PATTERN -----------------------

class SelectionStrategy(ABC):
    """Интерфейс за избор на най-подходящ транспорт."""

    name: str

    @abstractmethod
    def select(self, results: list[TransportResult]) -> Optional[TransportResult]:
        """Избира една от възможните опции (или None)."""

    @staticmethod
    def feasible(results: list[TransportResult]) -> list[TransportResult]:
        return [result for result in results if result.possible]


class FastestStrategy(SelectionStrategy):
    name = "Най-бърз"

    def select(self, results: list[TransportResult]) -> Optional[TransportResult]:
        feasible = self.feasible(results)
        if not feasible:
            return None
        return min(feasible, key=lambda item: (item.duration_min, item.total_cost_eur))


class CheapestStrategy(SelectionStrategy):
    name = "Най-евтин"

    def select(self, results: list[TransportResult]) -> Optional[TransportResult]:
        feasible = self.feasible(results)
        if not feasible:
            return None
        return min(feasible, key=lambda item: (item.total_cost_eur, item.duration_min))


class BalancedStrategy(SelectionStrategy):
    name = "Баланс време/цена"
    TIME_WEIGHT = 0.65
    COST_WEIGHT = 0.35

    def select(self, results: list[TransportResult]) -> Optional[TransportResult]:
        feasible = self.feasible(results)
        if not feasible:
            return None

        max_time = max(item.duration_min for item in feasible)
        max_cost = max(item.total_cost_eur for item in feasible)

        def score(item: TransportResult) -> tuple[float, float]:
            # Нормализиране: и времето, и цената попадат в [0, 1].
            relative_time = item.duration_min / max_time
            relative_cost = item.total_cost_eur / max_cost if max_cost > 0 else 0.0
            weighted = self.TIME_WEIGHT * relative_time + self.COST_WEIGHT * relative_cost
            return (weighted, item.duration_min)

        return min(feasible, key=score)


# ----------------------- FACADE PATTERN -----------------------

class TransportPlannerFacade:
    """Опростява работата с Factory, транспорта и Strategy в един метод."""

    def __init__(self, factory: Optional[TransportFactory] = None) -> None:
        self.factory = factory if factory is not None else TransportFactory()

    def analyze(
        self,
        route: Route,
        preferred_modes: list[str],
        strategy: SelectionStrategy,
    ) -> tuple[list[TransportResult], Optional[TransportResult]]:
        if not preferred_modes:
            raise ValueError("Изберете поне един вид транспорт.")

        # Запазваме реда на въвеждане, без повтарящи се видове.
        unique_modes = list(dict.fromkeys(preferred_modes))
        results = [self.factory.create(mode).evaluate(route) for mode in unique_modes]
        chosen = strategy.select(results)
        return results, chosen


# ----------------------- ГРАФИЧЕН ИНТЕРФЕЙС (TKINTER) -----------------------

import tkinter as tk
from tkinter import messagebox, ttk


class TransportPlannerGUI:
    """Потребителски интерфейс, който използва Facade, а не пресмята сам.

    Това е допълнението, изисквано за оценка Отличен 6.
    """

    TRANSPORT_CHOICES = [
        ("walk", "Пеша"),
        ("bike", "Велосипед"),
        ("car", "Автомобил"),
        ("bus", "Градски транспорт"),
    ]
    STRATEGY_CHOICES = {
        "Най-бърз": FastestStrategy,
        "Най-евтин": CheapestStrategy,
        "Баланс време/цена": BalancedStrategy,
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.planner = TransportPlannerFacade()
        self.root.title("Transport Planner | Задание 3 – Софтуерни шаблони")
        self.root.geometry("1100x700")
        self.root.minsize(890, 620)

        self.distance_var = tk.StringVar(value="12")
        self.fuel_price_var = tk.StringVar(value="1.55")
        self.public_var = tk.BooleanVar(value=True)
        self.bike_lanes_var = tk.BooleanVar(value=True)
        self.car_access_var = tk.BooleanVar(value=True)
        self.hilly_var = tk.BooleanVar(value=False)
        self.mode_vars = {
            code: tk.BooleanVar(value=True)
            for code, _ in self.TRANSPORT_CHOICES
        }
        self.strategy_var = tk.StringVar(value="Баланс време/цена")
        self.summary_var = tk.StringVar(value="Въведете параметри и натиснете „Изчисли“.")
        self.details_var = tk.StringVar(value="")

        self._setup_style()
        self._build_widgets()
        self.root.bind("<Return>", lambda _event: self.calculate())

    def _setup_style(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 17, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 10))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Results.Treeview", rowheight=30, font=("Segoe UI", 10))
        style.configure("Results.Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Recommendation.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=8)

    def _build_widgets(self) -> None:
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Избор на най-подходящ транспорт", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            main,
            text="Сравнение по време, цена и възможност за изминаване на маршрута",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 14))

        top = ttk.Frame(main)
        top.pack(fill="x")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)

        route_frame = ttk.LabelFrame(
            top, text="1. Параметри на маршрута", style="Section.TLabelframe", padding=12
        )
        route_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        route_frame.columnconfigure(1, weight=1)

        ttk.Label(route_frame, text="Дистанция (км):").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(route_frame, textvariable=self.distance_var, width=15).grid(
            row=0, column=1, sticky="ew", padx=(12, 0), pady=5
        )
        ttk.Label(route_frame, text="Гориво (€/литър):").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(route_frame, textvariable=self.fuel_price_var, width=15).grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=5
        )

        ttk.Checkbutton(
            route_frame, text="Има градски транспорт", variable=self.public_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(
            route_frame, text="Има велоалеи", variable=self.bike_lanes_var
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(
            route_frame, text="Разрешен е достъп с автомобил", variable=self.car_access_var
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=3)
        ttk.Checkbutton(
            route_frame, text="Хълмист терен", variable=self.hilly_var
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=3)

        preferences_frame = ttk.LabelFrame(
            top, text="2. Предпочитания", style="Section.TLabelframe", padding=12
        )
        preferences_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(preferences_frame, text="Видове транспорт:").pack(anchor="w", pady=(0, 5))
        for code, name in self.TRANSPORT_CHOICES:
            ttk.Checkbutton(
                preferences_frame, text=name, variable=self.mode_vars[code]
            ).pack(anchor="w", pady=3)

        ttk.Separator(preferences_frame, orient="horizontal").pack(fill="x", pady=11)
        ttk.Label(preferences_frame, text="Критерий за избор:").pack(anchor="w", pady=(0, 5))
        strategy_menu = ttk.Combobox(
            preferences_frame,
            textvariable=self.strategy_var,
            values=list(self.STRATEGY_CHOICES),
            state="readonly",
        )
        strategy_menu.pack(fill="x", pady=(0, 5))

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=14)
        ttk.Button(
            actions, text="Изчисли и сравни", style="Action.TButton", command=self.calculate
        ).pack(side="left", padx=(0, 10))
        ttk.Button(actions, text="Примерни стойности", command=self.load_demo).pack(
            side="left", padx=(0, 10)
        )
        ttk.Button(actions, text="Изчисти резултатите", command=self.clear_results).pack(
            side="left"
        )

        result_frame = ttk.LabelFrame(
            main, text="3. Резултати за избраните видове транспорт",
            style="Section.TLabelframe", padding=10,
        )
        result_frame.pack(fill="both", expand=True)

        columns = ("mode", "possible", "time", "fuel", "total", "note")
        self.table = ttk.Treeview(
            result_frame, columns=columns, show="headings", height=7, style="Results.Treeview"
        )
        headings = {
            "mode": "Транспорт",
            "possible": "Възможен",
            "time": "Време (мин)",
            "fuel": "Гориво (€)",
            "total": "Общо (€)",
            "note": "Пояснение",
        }
        widths = {"mode": 145, "possible": 85, "time": 115, "fuel": 105, "total": 105, "note": 400}
        for code in columns:
            self.table.heading(code, text=headings[code])
            self.table.column(code, width=widths[code], minwidth=80, stretch=(code == "note"))
        self.table.tag_configure("unavailable", foreground="#a33b3b")
        self.table.pack(side="left", fill="both", expand=True)
        vertical_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.table.yview)
        vertical_scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=vertical_scroll.set)

        summary_frame = ttk.Frame(main, padding=(1, 12, 1, 0))
        summary_frame.pack(fill="x")
        ttk.Label(
            summary_frame, textvariable=self.summary_var,
            style="Recommendation.TLabel", wraplength=1000,
        ).pack(anchor="w")
        ttk.Label(
            summary_frame, textvariable=self.details_var, wraplength=1000
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(
            main,
            text="* Примерен учебен модел: скорости, граници и цени са условни, без GPS или реални разписания.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(12, 0))

    @staticmethod
    def _parse_positive_number(raw: str, label: str) -> float:
        try:
            number = float(raw.strip().replace(",", "."))
        except ValueError:
            raise ValueError(f"{label}: въведете число, например 12.5.") from None
        if not isfinite(number) or number <= 0:
            raise ValueError(f"{label} трябва да бъде положително число.")
        return number

    def calculate(self) -> None:
        try:
            distance = self._parse_positive_number(self.distance_var.get(), "Дистанцията")
            fuel_price = self._parse_positive_number(self.fuel_price_var.get(), "Цената на горивото")
            route = Route(
                distance_km=distance,
                has_public_transport=self.public_var.get(),
                has_bike_lanes=self.bike_lanes_var.get(),
                car_access=self.car_access_var.get(),
                fuel_price_eur_per_liter=fuel_price,
                hilly=self.hilly_var.get(),
            )
            preferred = [
                code for code, _ in self.TRANSPORT_CHOICES if self.mode_vars[code].get()
            ]
            strategy_class = self.STRATEGY_CHOICES[self.strategy_var.get()]
            strategy = strategy_class()
            results, selected = self.planner.analyze(route, preferred, strategy)
        except (ValueError, KeyError) as error:
            messagebox.showerror("Невалидни данни", str(error), parent=self.root)
            return

        self.clear_results()
        for result in results:
            if result.possible:
                row = (
                    result.name, "ДА", f"{result.duration_min:.2f}",
                    f"{result.fuel_cost_eur:.2f}", f"{result.total_cost_eur:.2f}",
                    result.reason,
                )
                self.table.insert("", "end", values=row)
            else:
                self.table.insert(
                    "", "end",
                    values=(result.name, "НЕ", "—", "—", "—", result.reason),
                    tags=("unavailable",),
                )

        if selected is None:
            self.summary_var.set("Няма подходящ транспорт сред избраните варианти.")
            self.details_var.set("Променете условията на маршрута или избрания транспорт.")
        else:
            self.summary_var.set(f"Препоръка: {selected.name}  |  Критерий: {strategy.name}")
            self.details_var.set(
                f"Време: {selected.duration_min:.2f} мин   •   "
                f"Разход за гориво: {selected.fuel_cost_eur:.2f} €   •   "
                f"Общо за пътника: {selected.total_cost_eur:.2f} €"
            )

    def clear_results(self) -> None:
        for item in self.table.get_children():
            self.table.delete(item)
        self.summary_var.set("Въведете параметри и натиснете „Изчисли“.")
        self.details_var.set("")

    def load_demo(self) -> None:
        self.distance_var.set("12")
        self.fuel_price_var.set("1.55")
        self.public_var.set(True)
        self.bike_lanes_var.set(True)
        self.car_access_var.set(True)
        self.hilly_var.set(False)
        for value in self.mode_vars.values():
            value.set(True)
        self.strategy_var.set("Баланс време/цена")
        self.calculate()


def main() -> None:
    root = tk.Tk()
    TransportPlannerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
