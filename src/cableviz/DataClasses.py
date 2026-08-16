# -*- coding: utf-8 -*-

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from cableviz.cv_colors import COLOR_CODES, Color, ColorMode, Colors, ColorScheme
from cableviz.cv_helper import aspect_ratio, int2tuple

# Each type alias have their legal values described in comments - validation might be implemented in the future
PlainText = str  # Text not containing HTML tags nor newlines
Hypertext = str  # Text possibly including HTML hyperlinks that are removed in all outputs except HTML output
MultilineHypertext = (
    str  # Hypertext possibly also including newlines to break lines in diagram output
)

Designator = PlainText  # Case insensitive unique name of connector or cable

# Literal type aliases below are commented to avoid requiring python 3.8
ConnectorMultiplier = PlainText  # = Literal['pincount', 'populated', 'unpopulated']
CableMultiplier = (
    PlainText  # = Literal['wirecount', 'terminations', 'length', 'total_length']
)
ImageScale = PlainText  # = Literal['false', 'true', 'width', 'height', 'both']

# Type combinations
Pin = Union[int, PlainText]  # Pin identifier
PinIndex = int  # Zero-based pin index
Wire = Union[int, PlainText]  # Wire number or Literal['s'] for shield
NoneOrMorePins = Union[
    Pin, Tuple[Pin, ...], None
]  # None, one, or a tuple of pin identifiers
NoneOrMorePinIndices = Union[
    PinIndex, Tuple[PinIndex, ...], None
]  # None, one, or a tuple of zero-based pin indices
OneOrMoreWires = Union[Wire, Tuple[Wire, ...]]  # One or a tuple of wires

# Metadata can contain whatever is needed by the HTML generation/template.
MetadataKeys = PlainText  # Literal['title', 'description', 'notes', ...]


Side = Enum("Side", "LEFT RIGHT")


class Metadata(dict):
    pass


@dataclass
class Options:
    fontname: PlainText = "arial"
    bgcolor: Color = "WH"
    bgcolor_node: Optional[Color] = "WH"
    bgcolor_connector: Optional[Color] = None
    bgcolor_cable: Optional[Color] = None
    bgcolor_bundle: Optional[Color] = None
    color_mode: ColorMode = "SHORT"
    mini_bom_mode: bool = True
    template_separator: str = "."

    def __post_init__(self):
        if not self.bgcolor_node:
            self.bgcolor_node = self.bgcolor
        if not self.bgcolor_connector:
            self.bgcolor_connector = self.bgcolor_node
        if not self.bgcolor_cable:
            self.bgcolor_cable = self.bgcolor_node
        if not self.bgcolor_bundle:
            self.bgcolor_bundle = self.bgcolor_cable


@dataclass
class Tweak:
    override: Optional[Dict[Designator, Dict[str, Optional[str]]]] = None
    append: Union[str, List[str], None] = None


@dataclass
class Image:
    # Attributes of the image object <img>:
    src: str
    scale: Optional[ImageScale] = None
    # Attributes of the image cell <td> containing the image:
    width: Optional[int] = None
    height: Optional[int] = None
    fixedsize: Optional[bool] = None
    bgcolor: Optional[Color] = None
    # Contents of the text cell <td> just below the image cell:
    caption: Optional[MultilineHypertext] = None
    # See also HTML doc at https://graphviz.org/doc/info/shapes.html#html

    def __post_init__(self):
        if self.fixedsize is None:
            # Default True if any dimension specified unless self.scale also is specified.
            self.fixedsize = (self.width or self.height) and self.scale is None

        if self.scale is None:
            if not self.width and not self.height:
                self.scale = "false"
            elif self.width and self.height:
                self.scale = "both"
            else:
                self.scale = "true"  # When only one dimension is specified.

        if self.fixedsize:
            # If only one dimension is specified, compute the other
            # because Graphviz requires both when fixedsize=True.
            if self.height:
                if not self.width:
                    self.width = self.height * aspect_ratio(self.src)
            else:
                if self.width:
                    self.height = self.width / aspect_ratio(self.src)


@dataclass
class AdditionalComponent:
    type: MultilineHypertext
    subtype: Optional[MultilineHypertext] = None
    manufacturer: Optional[MultilineHypertext] = None
    mpn: Optional[MultilineHypertext] = None
    supplier: Optional[MultilineHypertext] = None
    spn: Optional[MultilineHypertext] = None
    pn: Optional[Hypertext] = None
    qty: float = 1
    unit: Optional[str] = None
    qty_multiplier: Union[ConnectorMultiplier, CableMultiplier, None] = None
    bgcolor: Optional[Color] = None

    @property
    def description(self) -> str:
        t = self.type.rstrip()
        st = f", {self.subtype.rstrip()}" if self.subtype else ""
        t = t + st
        return t


@dataclass
class Connector:
    name: Designator
    bgcolor: Optional[Color] = None
    bgcolor_title: Optional[Color] = None
    manufacturer: Optional[MultilineHypertext] = None
    mpn: Optional[MultilineHypertext] = None
    supplier: Optional[MultilineHypertext] = None
    spn: Optional[MultilineHypertext] = None
    pn: Optional[Hypertext] = None
    style: Optional[str] = None
    category: Optional[str] = None
    type: Optional[MultilineHypertext] = None
    subtype: Optional[MultilineHypertext] = None
    pincount: Optional[int] = None
    image: Optional[Image] = None
    notes: Optional[MultilineHypertext] = None
    pins: List[Pin] = field(default_factory=list)
    pinlabels: List[Pin] = field(default_factory=list)
    pincolors: List[Color] = field(default_factory=list)
    pin_terminals: List[Terminal] = field(default_factory=list)
    color: Optional[Color] = None
    show_name: Optional[bool] = None
    show_pincount: Optional[bool] = None
    hide_disconnected_pins: bool = False
    loops: List[List[Pin]] = field(default_factory=list)
    ignore_in_bom: bool = False
    additional_components: List[AdditionalComponent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.image, dict):
            self.image = Image(**self.image)

        self.ports_left = False
        self.ports_right = False
        self.visible_pins = {}

        if self.style == "simple":
            if self.pincount and self.pincount > 1:
                raise Exception(
                    "Connectors with style set to simple may only have one pin"
                )
            self.pincount = 1

        if not self.pincount:
            self.pincount = max(
                len(self.pins), len(self.pinlabels), len(self.pincolors)
            )
            if not self.pincount:
                raise Exception(
                    "You need to specify at least one, pincount, pins, pinlabels, or pincolors"
                )

        # create default list for pins (sequential) if not specified
        if not self.pins:
            self.pins = list(range(1, self.pincount + 1))

        if len(self.pins) != len(set(self.pins)):
            raise Exception("Pins are not unique")

        if self.show_name is None:
            # hide designators for simple and for auto-generated connectors by default
            self.show_name = self.style != "simple" and self.name[0:2] != "__"

        if self.show_pincount is None:
            # hide pincount for simple (1 pin) connectors by default
            self.show_pincount = self.style != "simple"

        for loop in self.loops:
            # TODO: allow using pin labels in addition to pin numbers, just like when defining regular connections
            # TODO: include properties of wire used to create the loop
            if len(loop) != 2:
                raise Exception("Loops must be between exactly two pins!")
            for pin in loop:
                if pin not in self.pins:
                    raise Exception(
                        f'Unknown loop pin "{pin}" for connector "{self.name}"!'
                    )
                # Make sure loop connected pins are not hidden.
                self.activate_pin(pin, None)

        for i, item in enumerate(self.additional_components):
            if isinstance(item, dict):
                self.additional_components[i] = AdditionalComponent(**item)

    def activate_pin(self, pin: Pin, side: Side) -> None:
        self.visible_pins[pin] = True
        if side == Side.LEFT:
            self.ports_left = True
        elif side == Side.RIGHT:
            self.ports_right = True

    def get_qty_multiplier(self, qty_multiplier: Optional[ConnectorMultiplier]) -> int:
        if not qty_multiplier:
            return 1
        elif qty_multiplier == "pincount":
            return self.pincount
        elif qty_multiplier == "populated":
            return sum(self.visible_pins.values())
        elif qty_multiplier == "unpopulated":
            return max(0, self.pincount - sum(self.visible_pins.values()))
        else:
            raise ValueError(
                f"invalid qty multiplier parameter for connector {qty_multiplier}"
            )


@dataclass
class Cable:
    name: Designator
    bgcolor: Optional[Color] = None
    bgcolor_title: Optional[Color] = None
    manufacturer: Union[MultilineHypertext, List[MultilineHypertext], None] = None
    mpn: Union[MultilineHypertext, List[MultilineHypertext], None] = None
    supplier: Union[MultilineHypertext, List[MultilineHypertext], None] = None
    spn: Union[MultilineHypertext, List[MultilineHypertext], None] = None
    pn: Union[Hypertext, List[Hypertext], None] = None
    category: Optional[str] = None
    type: Optional[MultilineHypertext] = None
    gauge: Optional[float] = None
    gauge_unit: Optional[str] = None
    show_equiv: bool = False
    length: float = None
    length_suffix: Optional[str] = None
    length_unit: str = None
    color: Optional[Color] = None
    wirecount: Optional[int] = None
    shield: Union[bool, Color] = False
    image: Optional[Image] = None
    notes: Optional[MultilineHypertext] = None
    colors: List[Colors] = field(default_factory=list)
    wirelabels: List[Wire] = field(default_factory=list)
    color_code: Optional[ColorScheme] = None
    show_name: Optional[bool] = None
    show_wirecount: bool = True
    show_wirenumbers: Optional[bool] = None
    ignore_in_bom: bool = False
    additional_components: List[AdditionalComponent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.image, dict):
            self.image = Image(**self.image)

        if isinstance(self.gauge, str):  # gauge and unit specified
            try:
                g, u = self.gauge.split(" ")
            except Exception:
                raise Exception(
                    f"Cable {self.name} gauge={self.gauge} - Gauge must be a number, or number and unit separated by a space"
                )
            self.gauge = g

            if self.gauge_unit is not None:
                print(
                    f"Warning: Cable {self.name} gauge_unit={self.gauge_unit} is ignored because its gauge contains {u}"
                )
            if u.upper() == "AWG":
                self.gauge_unit = u.upper()
            else:
                self.gauge_unit = u.replace("mm2", "mm\u00b2")

        elif self.gauge is not None:  # gauge specified, assume mm2
            if self.gauge_unit is None:
                self.gauge_unit = "mm\u00b2"
        else:
            pass  # gauge not specified

        if isinstance(self.length, (str, float, int)):

            #           Check there are no special characters in the length string, remove any spaces, then split the string at plus or minus signs
            try:
                self.length = str(self.length)
                self.length_suffix = ""
                self.length_unit = ""
                length_string_conditioned = self.length.replace(" ", "")
                if re.search(r"[^0-9a-zA-Z\.\+\-%]+", length_string_conditioned):
                    raise SyntaxError(
                        f"Error processing length information for cable {self.name}\nHint: Length information string must only contain letters, numbers, and the plus, minus, percent, and full stop symbols"
                    )
                else:
                    length_string_list = list(
                        filter(None, re.split("([+-])", length_string_conditioned))
                    )
            except Exception:
                raise SyntaxError(
                    f"Error processing wire length information for cable {self.name}\nHint: Length information must be a valid string - see documentation for more information"
                )
            # Pull out length unit or switch to mm
            try:
                if re.search(r"[a-zA-Z]+", self.length):
                    self.length_unit = re.search(r"[a-zA-Z]+", self.length).group(0)
                else:
                    self.length_unit = "mm"
            except Exception:
                raise SyntaxError(
                    f"Error processing wire length information for cable {self.name} - could not process length unit"
                )

            #           Store the substrings in variables
            length_prefix_none = ""
            length_prefix_plus = ""
            length_prefix_minus = ""

            try:
                for i, substring in enumerate(length_string_list):
                    if i == 0:
                        length_prefix_none = re.search(r"[0-9\.]+", substring).group(0)
                    elif substring == "+":
                        if length_string_list[i + 1] == "-":
                            length_prefix_plus = re.search(
                                r"[0-9\.]+", length_string_list[i + 2]
                            ).group(0)
                        else:
                            length_prefix_plus = re.search(
                                r"[0-9\.]+", length_string_list[i + 1]
                            ).group(0)
                    elif substring == "-" and not length_string_list[i - 1] == "+":
                        length_prefix_minus = re.search(
                            r"[0-9\.]+", length_string_list[i + 1]
                        ).group(0)
                    else:
                        pass
            except Exception:
                raise SyntaxError(
                    f"Error processing wire length information for cable {self.name}\nHint: Length information must not end with a plus or minus symbol - see documentation for more information"
                )

            #           Format the tolerance string to append to the length measurement based on the substrings found above
            try:
                self.length = float(length_prefix_none)
                if (
                    length_prefix_none != ""
                    and length_prefix_plus != ""
                    and length_prefix_minus == ""
                ):
                    self.length_suffix = " (± " + length_prefix_plus + ") "
                elif (
                    length_prefix_none != ""
                    and length_prefix_minus != ""
                    and length_prefix_plus == ""
                ):
                    self.length_suffix = " - " + length_prefix_minus + " "
                elif (
                    length_prefix_none != ""
                    and length_prefix_plus != ""
                    and length_prefix_minus != ""
                ):
                    self.length_suffix = (
                        " (+ "
                        + length_prefix_plus
                        + " / - "
                        + length_prefix_minus
                        + ") "
                    )
                else:
                    self.length_unit = " " + self.length_unit
            except Exception:
                raise Exception(
                    f"Error processing wire length information for cable {self.name}\nHint: See documentation for correct syntax"
                )

        self.connections = []

        if self.wirecount:  # number of wires explicitly defined
            if self.colors:  # use custom color palette (partly or looped if needed)
                pass
            elif self.color_code:
                # use standard color palette (partly or looped if needed)
                if self.color_code not in COLOR_CODES:
                    raise Exception("Unknown color code")
                self.colors = COLOR_CODES[self.color_code]
            else:  # no colors defined, add dummy colors
                self.colors = [""] * self.wirecount

            # make color code loop around if more wires than colors
            if self.wirecount > len(self.colors):
                m = self.wirecount // len(self.colors) + 1
                self.colors = self.colors * int(m)
            # cut off excess after looping
            self.colors = self.colors[: self.wirecount]
        else:  # wirecount implicit in length of color list
            if not self.colors:
                raise Exception(
                    "Unknown number of wires. Must specify wirecount or colors (implicit length)"
                )
            self.wirecount = len(self.colors)

        if self.wirelabels:
            if self.shield and "s" in self.wirelabels:
                raise Exception(
                    '"s" may not be used as a wire label for a shielded cable.'
                )

        # if lists of part numbers are provided check this is a bundle and that it matches the wirecount.
        for idfield in [self.manufacturer, self.mpn, self.supplier, self.spn, self.pn]:
            if isinstance(idfield, list):
                if self.category == "bundle":
                    # check the length
                    if len(idfield) != self.wirecount:
                        raise Exception("lists of part data must match wirecount")
                else:
                    raise Exception("lists of part data are only supported for bundles")

        if self.show_name is None:
            # hide designators for auto-generated cables by default
            self.show_name = self.name[0:2] != "__"

        if self.show_wirenumbers is None:
            # by default, show wire numbers for cables, hide for bundles
            self.show_wirenumbers = self.category != "bundle"

        for i, item in enumerate(self.additional_components):
            if isinstance(item, dict):
                self.additional_components[i] = AdditionalComponent(**item)

    # The *_pin arguments accept a tuple, but it seems not in use with the current code.
    def connect(
        self,
        from_name: Optional[Designator],
        from_pin: NoneOrMorePinIndices,
        via_wire: OneOrMoreWires,
        to_name: Optional[Designator],
        to_pin: NoneOrMorePinIndices,
    ) -> None:
        from_pin = int2tuple(from_pin)
        via_wire = int2tuple(via_wire)
        to_pin = int2tuple(to_pin)
        if len(from_pin) != len(to_pin):
            raise Exception("from_pin must have the same number of elements as to_pin")
        for i, _ in enumerate(from_pin):
            self.connections.append(
                Connection(from_name, from_pin[i], via_wire[i], to_name, to_pin[i])
            )

    def get_qty_multiplier(self, qty_multiplier: Optional[CableMultiplier]) -> float:
        if not qty_multiplier:
            return 1
        elif qty_multiplier == "wirecount":
            return self.wirecount
        elif qty_multiplier == "terminations":
            return len(self.connections)
        elif qty_multiplier == "length":
            return self.length
        elif qty_multiplier == "total_length":
            return self.length * self.wirecount
        else:
            raise ValueError(
                f"invalid qty multiplier parameter for cable {qty_multiplier}"
            )


@dataclass
class Connection:
    from_name: Optional[Designator]
    from_pin: Optional[Pin]
    via_port: Wire
    to_name: Optional[Designator]
    to_pin: Optional[Pin]


@dataclass
class MatePin:
    from_name: Designator
    from_pin: Pin
    to_name: Designator
    to_pin: Pin
    shape: str


@dataclass
class MateComponent:
    from_name: Designator
    to_name: Designator
    shape: str
