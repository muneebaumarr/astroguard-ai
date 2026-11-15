"""Versioned, read-only educational catalog. No patient records or network calls."""
from datetime import date
from astroguard_contracts import dto as d

REVIEWED_ON = date(2026, 11, 15)
LIMITATION = "General education only, not individual medical advice or a validated intervention. AstroGuard observations are fictional; NASA sources do not endorse this prototype."


def source(title, url):
    return d.SourceReference(title=title, url=url)


RADIATION = source('NASA: Space Radiation', 'https://www.nasa.gov/hrp/hazard-space-radiation/')
ISOLATION = source('NASA: Isolation and Confinement', 'https://www.nasa.gov/hrp/hazard-isolation-and-confinement/')
DISTANCE = source('NASA: Distance From Earth', 'https://www.nasa.gov/hrp/hazard-distance-from-earth/')
GRAVITY = source('NASA: Gravity Fields', 'https://www.nasa.gov/hrp/hazard-gravity-fields/')
CABIN = source('NASA: Hostile/Closed Environments', 'https://www.nasa.gov/hrp/hazard-hostile-closed-environments/')
SLEEP = source('NASA: Inadequate Sleep and Irregular Schedules', 'https://www.nasa.gov/reference/risk-from-inadequate-sleep-and-irregular-schedules/')
HEALTH = source('NASA: Fundamentals of Human Health', 'https://www.nasa.gov/reference/fundamentals-of-human-health/')

_HAZARDS = (
    d.Hazard(slug='space_radiation', title='Space Radiation', related_indicators=['radiation_dose_rate'], references=[RADIATION],
        description='Why it matters: Beyond Earth’s protective environment, radiation is an important mission-planning challenge.\n\nCrew and operations: Exposure can affect biological systems and complicates long-duration exploration.\n\nPreparedness concepts: Shielding design, radiation research and exposure monitoring inform mission preparation.',
        monitoring_limitations='Radiation monitoring needs exposure history and mission context. A fictional cabin rate is not personal dosimetry, accumulated dose or a prediction of injury.'),
    d.Hazard(slug='isolation_confinement', title='Isolation and Confinement', related_indicators=[], references=[ISOLATION],
        description='Why it matters: Long missions place small teams together in restricted spaces, away from familiar support.\n\nCrew and operations: Communication, sleep and team functioning can be affected, influencing coordinated work.\n\nPreparedness concepts: Crew preparation, supportive communication and planned routines are general areas of research and mission support.',
        monitoring_limitations='Self-reported mood and stress offer limited context. They cannot establish isolation effects or diagnose a mental health condition.'),
    d.Hazard(slug='distance_from_earth', title='Distance from Earth', related_indicators=[], references=[DISTANCE],
        description='Why it matters: Greater distance makes timely assistance and resupply harder.\n\nCrew and operations: Communication delays and limited evacuation options increase the importance of onboard resources and independent operations.\n\nPreparedness concepts: Training, resource planning and tools that support crew autonomy are central educational themes.',
        monitoring_limitations='Vital signs cannot measure communication delay, readiness for evacuation or mission self-sufficiency. AstroGuard does not simulate these capabilities.'),
    d.Hazard(slug='gravity_fields', title='Gravity Fields', related_indicators=[], references=[GRAVITY],
        description='Why it matters: Moving among different gravity environments requires bodily adaptation.\n\nCrew and operations: Changes involving muscles, bones and balance can influence movement and mission tasks.\n\nPreparedness concepts: Conditioning, exercise research and preparation for transitions between gravity environments support mission planning.',
        monitoring_limitations='Heart rate alone cannot establish bone loss, muscle loss or gravity adaptation. This prototype does not measure those outcomes.'),
    d.Hazard(slug='hostile_closed_environments', title='Hostile and Closed Environments', related_indicators=['cabin_co2'], references=[CABIN],
        description='Why it matters: A spacecraft must sustain a habitable enclosed environment.\n\nCrew and operations: Air quality, noise, lighting and other habitat conditions influence living and working aboard the vehicle.\n\nPreparedness concepts: Habitat design, environmental monitoring and equipment maintenance are important general considerations.',
        monitoring_limitations='Cabin CO2 is only one environmental observation. Astronaut oxygen saturation is not cabin oxygen concentration. No single value establishes habitat safety.'),
)


def article(slug, title, indicators, hazards, text, references):
    return d.GuidanceArticle(slug=slug, title=title, indicators=indicators, hazard_slugs=hazards,
        educational_text=text, limitations=LIMITATION, references=references, reviewed_on=REVIEWED_ON)


_GUIDANCE = (
    article('sleep_circadian', 'Sleep and circadian rhythm', [], ['isolation_confinement'],
        'Spaceflight context: Irregular light-dark exposure and demanding schedules can disrupt rest.\n\nEducational considerations: Learn how planned sleep opportunities, lighting and work-rest scheduling support crew routines. A recorded sleep duration does not measure sleep quality or establish a sleep disorder.', [SLEEP]),
    article('exercise_conditioning', 'Physical exercise and conditioning', ['heart_rate'], ['gravity_fields'],
        'Spaceflight context: Altered gravity changes physical loading during daily activity.\n\nEducational considerations: Exercise equipment and conditioning programs are studied as mission countermeasures. An activity entry provides context, not an assessment of fitness or an exercise prescription.', [HEALTH, GRAVITY]),
    article('hydration_nutrition', 'Hydration and nutrition', [], ['hostile_closed_environments'],
        'Spaceflight context: Food systems and water availability are important parts of mission resource planning.\n\nEducational considerations: Learn about food acceptability, storage and nutrition planning alongside hydration research. AstroGuard does not record intake or determine nutritional needs; it cannot prescribe a diet or fluid target.', [HEALTH]),
    article('crew_wellbeing', 'Crew mental wellbeing', [], ['isolation_confinement'],
        'Spaceflight context: Isolated teams depend on communication and behavioral support.\n\nEducational considerations: Supportive team routines and opportunities to communicate are useful study topics. Self-reported mood or stress does not identify a mental health condition or prove that isolation caused a response.', [ISOLATION]),
    article('environmental_monitoring', 'Environmental monitoring and oxygen observations', ['cabin_co2', 'spo2'], ['hostile_closed_environments'],
        'Spaceflight context: Habitat systems and environmental observations provide complementary information.\n\nEducational considerations: Compare sensor meaning, timestamps and limitations. Cabin CO2 and astronaut oxygen saturation are different measurements; neither alone identifies a cause or confirms habitat safety. This topic is not a response procedure.', [CABIN]),
    article('radiation_awareness', 'Radiation awareness', ['radiation_dose_rate'], ['space_radiation'],
        'Spaceflight context: Radiation is considered during exploration planning.\n\nEducational considerations: Learn the distinction between a rate observation and accumulated exposure. Fictional cabin radiation telemetry cannot estimate personal exposure or biological effects. Shielding and exposure monitoring are research and engineering topics, not instructions generated by this app.', [RADIATION]),
)


def hazards():
    return [item.model_copy(deep=True) for item in _HAZARDS]


def guidance():
    return [item.model_copy(deep=True) for item in _GUIDANCE]
