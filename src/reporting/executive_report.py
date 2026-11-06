from dataclasses import dataclass, field


@dataclass
class ExecutiveKPI:
    label: str
    value: str


@dataclass
class ExecutiveScenario:
    name: str
    value: float | None
    formatted_value: str


@dataclass
class ExecutiveReport:
    title: str
    subtitle: str
    kpis: list[ExecutiveKPI] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    scenarios: list[ExecutiveScenario] = field(default_factory=list)