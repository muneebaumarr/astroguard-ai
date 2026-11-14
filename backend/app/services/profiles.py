from astroguard_contracts import dto as d
from astroguard_contracts.repositories import UnitOfWork


class ProfileService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def missions(self, query: d.MissionQuery) -> d.Page[d.Mission]:
        return self.uow.missions.list(query)

    def mission(self, id: d.UUIDString) -> d.Mission | None:
        return self.uow.missions.get(id)

    def astronauts(self, query: d.AstronautQuery) -> d.Page[d.Astronaut]:
        return self.uow.astronauts.list(query)

    def astronaut(self, id: d.UUIDString) -> d.Astronaut | None:
        return self.uow.astronauts.get(id)
