from __future__ import annotations

import collections
from typing import Dict, Final, List, Union


class FilterMixin:
    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(tuple(sorted(self.__dict__.items())))

    @property
    def changed(self) -> bool:
        return self != self.__class__.default()


class Volume(FilterMixin):
    def __init__(self, value: float):
        self.value = value

    def __float__(self):
        return self.value

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float):
        if v < 0:
            raise ValueError(f"Volume must be must be greater than or equals to zero, not {v}")
        self._value = float(v)

    @classmethod
    def default(cls) -> Volume:
        return cls(value=1.0)

    def increase(self, by: float = 5.0) -> None:
        self.value += by

    def decrease(self, by: float = 5.0) -> None:
        self.value -= by

    def reset(self) -> None:
        self.value = 1.0

    def get(self) -> float:
        return self.value

    def __repr__(self):
        return str(self.value)


# Implementation taken from https://github.com/PythonistaGuild/Wavelink/blob/master/wavelink/eqs.py
# TODO: MERGE: Add reference to MIT License from Wavelink
# Theres literally 0 reason to reimplement this specially since we will be moving over to Wavelink in the near future.
class Equalizer(FilterMixin):
    """Class representing a usable equalizer.
    Parameters
    ------------
    levels: List[Tuple[int, float]]
        A list of tuple pairs containing a band int and gain float.
    name: str
        An Optional string to name this Equalizer. Defaults to 'CustomEqualizer'
    Attributes
    ------------
    eq: list
        A list of {'band': int, 'gain': float}
    raw: list
        A list of tuple pairs containing a band int and gain float.
    """

    def __init__(self, *, levels: list, name: str = "CustomEqualizer"):
        self.band_count: Final[int] = 15
        self._eq = self._factory(levels)
        self._index = dict((d["band"], dict(d, index=index)) for (index, d) in enumerate(self._eq))
        self._raw = levels

        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return f"<RedLavalink.filters.Equalizer: {self._name}, Raw: {self._eq}>"

    @property
    def name(self) -> str:
        """The Equalizers friendly name."""
        return self._name

    def _factory(self, levels: list) -> List[Dict[str, Union[int, float]]]:

        if isinstance(levels[0], dict):
            pass
        elif isinstance(levels[0], (int, float)):
            levels = [
                dict(zip(["band", "gain"], values))
                for values in list(zip(list(range(self.band_count)), levels))
            ]
        elif isinstance(levels[0], tuple):
            levels = [dict(zip(["band", "gain"], values)) for values in levels]
        else:
            raise TypeError("Equalizer levels should be a list of dictionaries.")

        _dict = collections.defaultdict(float)
        _dict.update((d.values() for d in levels))
        _dict = [{"band": i, "gain": _dict[i]} for i in range(self.band_count)]

        return _dict

    @classmethod
    def build(cls, *, levels: list, name: str = "CustomEqualizer") -> Equalizer:
        """Build a custom Equalizer class with the provided levels.
        Parameters
        ------------
        levels: List[Dict[str, Union[int, float]]]
            [
            {"band": 0, "gain": 0.0},
            {"band": 1, "gain": 0.0},
            ...
            ]
        name: str
            An Optional string to name this Equalizer. Defaults to 'CustomEqualizer'
        """
        return cls(levels=levels, name=name)

    @classmethod
    def flat(cls) -> Equalizer:
        """Flat Equalizer.
        Resets your EQ to Flat.
        """
        levels = [
            {"band": 0, "gain": 0.0},
            {"band": 1, "gain": 0.0},
            {"band": 2, "gain": 0.0},
            {"band": 3, "gain": 0.0},
            {"band": 4, "gain": 0.0},
            {"band": 5, "gain": 0.0},
            {"band": 6, "gain": 0.0},
            {"band": 7, "gain": 0.0},
            {"band": 8, "gain": 0.0},
            {"band": 9, "gain": 0.0},
            {"band": 10, "gain": 0.0},
            {"band": 11, "gain": 0.0},
            {"band": 12, "gain": 0.0},
            {"band": 13, "gain": 0.0},
            {"band": 14, "gain": 0.0},
        ]

        return cls(levels=levels, name="Flat")

    @classmethod
    def boost(cls) -> Equalizer:
        """Boost Equalizer.
        This equalizer emphasizes Punchy Bass and Crisp Mid-High tones.
        Not suitable for tracks with Deep/Low Bass.
        """
        levels = [
            {"band": 0, "gain": -0.075},
            {"band": 1, "gain": 0.125},
            {"band": 2, "gain": 0.125},
            {"band": 3, "gain": 0.1},
            {"band": 4, "gain": 0.1},
            {"band": 5, "gain": 0.05},
            {"band": 6, "gain": 0.075},
            {"band": 7, "gain": 0.0},
            {"band": 8, "gain": 0.0},
            {"band": 9, "gain": 0.0},
            {"band": 10, "gain": 0.0},
            {"band": 11, "gain": 0.0},
            {"band": 12, "gain": 0.125},
            {"band": 13, "gain": 0.15},
            {"band": 14, "gain": 0.05},
        ]

        return cls(levels=levels, name="Boost")

    @classmethod
    def metal(cls) -> Equalizer:
        """Experimental Metal/Rock Equalizer.
        Expect clipping on Bassy songs.
        """
        levels = [
            {"band": 0, "gain": 0.0},
            {"band": 1, "gain": 0.1},
            {"band": 2, "gain": 0.1},
            {"band": 3, "gain": 0.15},
            {"band": 4, "gain": 0.13},
            {"band": 5, "gain": 0.1},
            {"band": 6, "gain": 0.0},
            {"band": 7, "gain": 0.125},
            {"band": 8, "gain": 0.175},
            {"band": 9, "gain": 0.175},
            {"band": 10, "gain": 0.125},
            {"band": 11, "gain": 0.125},
            {"band": 12, "gain": 0.1},
            {"band": 13, "gain": 0.075},
            {"band": 14, "gain": 0.0},
        ]

        return cls(levels=levels, name="Metal")

    @classmethod
    def piano(cls) -> Equalizer:
        """Piano Equalizer.
        Suitable for Piano tracks, or tacks with an emphasis on Female Vocals.
        Could also be used as a Bass Cutoff.
        """
        levels = [
            {"band": 0, "gain": -0.25},
            {"band": 1, "gain": -0.25},
            {"band": 2, "gain": -0.125},
            {"band": 3, "gain": 0.0},
            {"band": 4, "gain": 0.25},
            {"band": 5, "gain": 0.25},
            {"band": 6, "gain": 0.0},
            {"band": 7, "gain": -0.25},
            {"band": 8, "gain": -0.25},
            {"band": 9, "gain": 0.0},
            {"band": 10, "gain": 0.0},
            {"band": 11, "gain": 0.5},
            {"band": 12, "gain": 0.25},
            {"band": 13, "gain": -0.025},
            {"band": 14, "gain": 0.0},
        ]

        return cls(levels=levels, name="Piano")

    @classmethod
    def default(cls) -> Equalizer:
        return cls.flat()

    def get(self) -> List[Dict[str, Union[int, float]]]:
        return self._eq

    def reset(self) -> None:
        eq = Equalizer.flat()
        self._eq = eq._eq
        self._name = eq._name
        self._raw = eq._raw

    def set_gain(self, band: int, gain: float) -> None:
        if band < 0 or band >= self.band_count:
            raise IndexError(f"Band {band} does not exist!")

        gain = float(min(max(gain, -0.25), 1.0))
        band = next((index for (index, d) in enumerate(self._eq) if d["band"] == band), None)
        self._eq[band]["gain"] = gain

    def get_gain(self, band: int) -> float:
        if band < 0 or band >= self.band_count:
            raise IndexError(f"Band {band} does not exist!")
        return self._index[band].get("gain", 0.0)

    def visualise(self):
        block = ""
        bands = [str(band + 1).zfill(2) for band in range(self.band_count)]
        bottom = (" " * 8) + " ".join(bands)
        gains = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.25]

        for gain in gains:
            prefix = ""
            if gain > 0:
                prefix = "+"
            elif gain == 0:
                prefix = " "

            block += f"{prefix}{gain:.2f} | "

            for value in self._eq:
                cur_gain = value.get("gain", 0.0)
                if cur_gain >= gain:
                    block += "[] "
                else:
                    block += "   "

            block += "\n"

        block += bottom
        return block


class Karaoke(FilterMixin):
    def __init__(self, level: float, mono_level: float, filter_band: float, filter_width: float):
        self.level = level
        self.mono_level = mono_level
        self.filter_band = filter_band
        self.filter_width = filter_width

    @property
    def level(self) -> float:
        return self._level

    @level.setter
    def level(self, v: float):
        self._level = float(v)

    @property
    def mono_level(self) -> float:
        return self._mono_level

    @mono_level.setter
    def mono_level(self, v: float):
        self._mono_level = float(v)

    @property
    def filter_band(self) -> float:
        return self._filter_band

    @filter_band.setter
    def filter_band(self, v: float):
        self._filter_band = float(v)

    @property
    def filter_width(self) -> float:
        return self._filter_width

    @filter_width.setter
    def filter_width(self, v: float):
        self._filter_width = float(v)

    @classmethod
    def default(cls) -> Karaoke:
        return cls(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)

    def get(self) -> Dict[str, float]:
        return {
            "level": self.level,
            "monoLevel": self.mono_level,
            "filterBand": self.filter_band,
            "filterWidth": self.filter_width,
        }

    def reset(self) -> None:
        self.level = 1.0
        self.mono_level = 1.0
        self.filter_band = 220.0
        self.filter_width = 100.0


class Timescale(FilterMixin):
    def __init__(self, speed: float, pitch: float, rate: float):
        self.speed = speed
        self.pitch = pitch
        self.rate = rate

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, v: float):
        self._speed = float(v)

    @property
    def pitch(self) -> float:
        return self._pitch

    @pitch.setter
    def pitch(self, v: float):
        self._pitch = float(v)

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    def rate(self, v: float):
        self._rate = float(v)

    @classmethod
    def default(cls) -> Timescale:
        return cls(speed=1.0, pitch=1.0, rate=1.0)

    def get(self) -> Dict[str, float]:
        return {
            "speed": self.speed,
            "pitch": self.pitch,
            "rate": self.rate,
        }

    def reset(self) -> None:
        self.speed = 1.0
        self.pitch = 1.0
        self.rate = 1.0


class Tremolo(FilterMixin):
    def __init__(self, frequency: float, depth: float):
        self.frequency = frequency
        self.depth = depth

    @property
    def frequency(self) -> float:
        return self._frequency

    @frequency.setter
    def frequency(self, v: float):
        if v <= 0:
            raise ValueError(f"Frequency must be must be greater than 0, not {v}")
        self._frequency = float(v)

    @property
    def depth(self) -> float:
        return self._depth

    @depth.setter
    def depth(self, v: float):
        if not (0.0 < v <= 1.0):
            raise ValueError(f"Depth must be must be 0.0 < x ≤ 1.0, not {v}")
        self._depth = float(v)

    @classmethod
    def default(cls) -> Tremolo:
        return cls(frequency=2.0, depth=0.5)

    def get(self) -> Dict[str, float]:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
        }

    def reset(self) -> None:
        self.frequency = 2.0
        self.depth = 0.5  # TODO: Testing:  According to LL Code setting this to 0 disableds it .... but 0.5 is also the default.


class Vibrato(FilterMixin):
    def __init__(self, frequency: float, depth: float):
        self.frequency = frequency
        self.depth = depth

    @property
    def frequency(self) -> float:
        return self._frequency

    @frequency.setter
    def frequency(self, v: float):
        if not (0.0 < v <= 14.0):
            raise ValueError(f"Frequency must be must be 0.0 < v <= 14.0, not {v}")
        self._frequency = float(v)

    @property
    def depth(self) -> float:
        return self._depth

    @depth.setter
    def depth(self, v: float):
        if not (0.0 < v <= 1.0):
            raise ValueError(f"Depth must be must be 0.0 < x ≤ 1.0, not {v}")
        self._depth = float(v)

    @classmethod
    def default(cls) -> Vibrato:
        return cls(frequency=2.0, depth=0.5)

    def get(self) -> Dict[str, float]:
        return {
            "frequency": self.frequency,
            "depth": self.depth,
        }

    def reset(self) -> None:
        self.frequency = 2.0
        self.depth = 0.5  # TODO: Testing: Check: According to LL Code setting this to 0 disableds it .... but 0.5 is also the default.


class Rotation(FilterMixin):
    def __init__(self, hertz: float):
        self.hertz = hertz

    @property
    def hertz(self) -> float:
        return self._hertz

    @hertz.setter
    def hertz(self, v: float):
        self._hertz = float(v)

    @classmethod
    def default(cls) -> Rotation:
        return cls(hertz=0.0)

    def get(self) -> Dict[str, float]:
        return {
            "rotationHz": self.hertz,
        }

    def reset(self) -> None:
        self.hertz = 0.0


class Distortion(FilterMixin):
    def __init__(
        self,
        sin_offset: float,
        sin_scale: float,
        cos_offset: float,
        cos_scale: float,
        tan_offset: float,
        tan_scale: float,
        offset: float,
        scale: float,
    ):
        self.sin_offset = sin_offset
        self.sin_scale = sin_scale
        self.cos_offset = cos_offset
        self.cos_scale = cos_scale
        self.tan_offset = tan_offset
        self.tan_scale = tan_scale
        self.offset = offset
        self.scale = scale

    @property
    def sin_offset(self) -> float:
        return self._sin_offset

    @sin_offset.setter
    def sin_offset(self, v: float):
        self._sin_offset = float(v)

    @property
    def sin_scale(self) -> float:
        return self._sin_scale

    @sin_scale.setter
    def sin_scale(self, v: float):
        self._sin_scale = float(v)

    @property
    def cos_offset(self) -> float:
        return self._cos_offset

    @cos_offset.setter
    def cos_offset(self, v: float):
        self._cos_offset = float(v)

    @property
    def cos_scale(self) -> float:
        return self._cos_scale

    @cos_scale.setter
    def cos_scale(self, v: float):
        self._cos_scale = float(v)

    @property
    def tan_offset(self) -> float:
        return self._tan_offset

    @tan_offset.setter
    def tan_offset(self, v: float):
        self._tan_offset = float(v)

    @property
    def tan_scale(self) -> float:
        return self._tan_scale

    @tan_scale.setter
    def tan_scale(self, v: float):
        self._tan_scale = float(v)

    @property
    def offset(self) -> float:
        return self._offset

    @offset.setter
    def offset(self, v: float):
        self._offset = float(v)

    @property
    def scale(self) -> float:
        return self._scale

    @scale.setter
    def scale(self, v: float):
        self._scale = float(v)

    @classmethod
    def default(cls) -> Distortion:
        return cls(
            sin_offset=0.0,
            sin_scale=1.0,
            cos_offset=0.0,
            cos_scale=1.0,
            tan_offset=0.0,
            tan_scale=1.0,
            offset=0.0,
            scale=1.0,
        )

    def get(self) -> Dict[str, float]:
        return {
            "sinOffset": self.sin_offset,
            "sinScale": self.sin_scale,
            "cosOffset": self.cos_offset,
            "cosScale": self.cos_scale,
            "tanOffset": self.tan_offset,
            "tanScale": self.tan_scale,
            "offset": self.offset,
            "scale": self.scale,
        }

    def reset(self) -> None:
        self.sin_offset = 0.0
        self.sin_scale = 1.0
        self.cos_offset = 0.0
        self.cos_scale = 1.0
        self.tan_offset = 0.0
        self.tan_scale = 1.0
        self.offset = 0.0
        self.scale = 1.0
