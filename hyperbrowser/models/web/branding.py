from __future__ import annotations
from typing import Literal, Optional, List, Union
from pydantic import BaseModel, ConfigDict, Field


# Typed response shape for the branding extraction output. Every field is
# Optional because the server may return a partial profile (e.g. when the
# LLM refuses or fails). `extra="allow"` on each model keeps the SDK forward-
# compatible if the server adds new keys — unknown fields become available
# via `model.model_extra`.


BrandingColorScheme = Literal["light", "dark"]

BrandingPersonalityTone = Literal[
    "professional",
    "playful",
    "modern",
    "traditional",
    "minimalist",
    "bold",
]

BrandingPersonalityEnergy = Literal["low", "medium", "high"]

# Known values listed for IDE hints; any string is accepted so the SDK
# doesn't need a version bump when the server's LLM starts emitting a new
# role / framework label. Pydantic's Union matches the Literal arm first
# for known values (preserving the tighter type), then falls through to
# `str` for anything else.
BrandingFontRole = Union[
    Literal["heading", "body", "monospace", "display", "unknown"],
    str,
]

BrandingDesignFramework = Union[
    Literal[
        "tailwind",
        "bootstrap",
        "material",
        "chakra",
        "custom",
        "unknown",
    ],
    str,
]


class BrandingColors(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    primary: Optional[str] = None
    secondary: Optional[str] = None
    accent: Optional[str] = None
    background: Optional[str] = None
    text_primary: Optional[str] = Field(
        default=None, alias="textPrimary", serialization_alias="textPrimary"
    )
    text_secondary: Optional[str] = Field(
        default=None, alias="textSecondary", serialization_alias="textSecondary"
    )
    link: Optional[str] = None
    success: Optional[str] = None
    warning: Optional[str] = None
    error: Optional[str] = None


class BrandingFont(BaseModel):
    model_config = ConfigDict(extra="allow")

    family: str
    role: Optional[BrandingFontRole] = None


class BrandingBorderRadiusCorners(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    top_left: Optional[str] = Field(
        default=None, alias="topLeft", serialization_alias="topLeft"
    )
    top_right: Optional[str] = Field(
        default=None, alias="topRight", serialization_alias="topRight"
    )
    bottom_right: Optional[str] = Field(
        default=None, alias="bottomRight", serialization_alias="bottomRight"
    )
    bottom_left: Optional[str] = Field(
        default=None, alias="bottomLeft", serialization_alias="bottomLeft"
    )


class BrandingButtonStyle(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    background: Optional[str] = None
    text_color: Optional[str] = Field(
        default=None, alias="textColor", serialization_alias="textColor"
    )
    border_color: Optional[str] = Field(
        default=None, alias="borderColor", serialization_alias="borderColor"
    )
    border_radius: Optional[str] = Field(
        default=None, alias="borderRadius", serialization_alias="borderRadius"
    )
    border_radius_corners: Optional[BrandingBorderRadiusCorners] = Field(
        default=None,
        alias="borderRadiusCorners",
        serialization_alias="borderRadiusCorners",
    )
    shadow: Optional[str] = None


class BrandingInputStyle(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    background: Optional[str] = None
    text_color: Optional[str] = Field(
        default=None, alias="textColor", serialization_alias="textColor"
    )
    border_color: Optional[str] = Field(
        default=None, alias="borderColor", serialization_alias="borderColor"
    )
    focus_border_color: Optional[str] = Field(
        default=None,
        alias="focusBorderColor",
        serialization_alias="focusBorderColor",
    )
    border_radius: Optional[str] = Field(
        default=None, alias="borderRadius", serialization_alias="borderRadius"
    )
    border_radius_corners: Optional[BrandingBorderRadiusCorners] = Field(
        default=None,
        alias="borderRadiusCorners",
        serialization_alias="borderRadiusCorners",
    )
    shadow: Optional[str] = None


class BrandingComponents(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    button_primary: Optional[BrandingButtonStyle] = Field(
        default=None, alias="buttonPrimary", serialization_alias="buttonPrimary"
    )
    button_secondary: Optional[BrandingButtonStyle] = Field(
        default=None,
        alias="buttonSecondary",
        serialization_alias="buttonSecondary",
    )
    input: Optional[BrandingInputStyle] = None


class BrandingFontFamilies(BaseModel):
    model_config = ConfigDict(extra="allow")

    primary: Optional[str] = None
    heading: Optional[str] = None
    code: Optional[str] = None


class BrandingFontStacks(BaseModel):
    model_config = ConfigDict(extra="allow")

    primary: Optional[List[str]] = None
    heading: Optional[List[str]] = None
    body: Optional[List[str]] = None
    paragraph: Optional[List[str]] = None


class BrandingFontSizes(BaseModel):
    model_config = ConfigDict(extra="allow")

    h1: Optional[str] = None
    h2: Optional[str] = None
    h3: Optional[str] = None
    body: Optional[str] = None
    small: Optional[str] = None


class BrandingTypography(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    font_families: Optional[BrandingFontFamilies] = Field(
        default=None, alias="fontFamilies", serialization_alias="fontFamilies"
    )
    font_stacks: Optional[BrandingFontStacks] = Field(
        default=None, alias="fontStacks", serialization_alias="fontStacks"
    )
    font_sizes: Optional[BrandingFontSizes] = Field(
        default=None, alias="fontSizes", serialization_alias="fontSizes"
    )
    line_heights: Optional[dict[str, Optional[float]]] = Field(
        default=None, alias="lineHeights", serialization_alias="lineHeights"
    )
    font_weights: Optional[dict[str, Optional[float]]] = Field(
        default=None, alias="fontWeights", serialization_alias="fontWeights"
    )


class BrandingSpacing(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    base_unit: Optional[float] = Field(
        default=None, alias="baseUnit", serialization_alias="baseUnit"
    )
    border_radius: Optional[str] = Field(
        default=None, alias="borderRadius", serialization_alias="borderRadius"
    )
    # LLM-extracted dicts — individual entries may be null when the model
    # couldn't measure a specific size bucket. Parallel to the typing used
    # on line_heights / font_weights above.
    padding: Optional[dict[str, Optional[float]]] = None
    margins: Optional[dict[str, Optional[float]]] = None
    grid_gutter: Optional[float] = Field(
        default=None, alias="gridGutter", serialization_alias="gridGutter"
    )


class BrandingImages(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    logo: Optional[str] = None
    logo_href: Optional[str] = Field(
        default=None, alias="logoHref", serialization_alias="logoHref"
    )
    logo_alt: Optional[str] = Field(
        default=None, alias="logoAlt", serialization_alias="logoAlt"
    )
    favicon: Optional[str] = None
    og_image: Optional[str] = Field(
        default=None, alias="ogImage", serialization_alias="ogImage"
    )


class BrandingPersonality(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    tone: Optional[BrandingPersonalityTone] = None
    energy: Optional[BrandingPersonalityEnergy] = None
    target_audience: Optional[str] = Field(
        default=None,
        alias="targetAudience",
        serialization_alias="targetAudience",
    )


class BrandingDesignSystem(BaseModel):
    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    framework: Optional[BrandingDesignFramework] = None
    component_library: Optional[str] = Field(
        default=None,
        alias="componentLibrary",
        serialization_alias="componentLibrary",
    )


class BrandingConfidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    buttons: Optional[float] = None
    colors: Optional[float] = None
    overall: Optional[float] = None


class BrandingProfile(BaseModel):
    """
    Typed response shape for the ``branding`` output format.
    All fields are optional; use ``model.model_extra`` to read server-added
    keys not represented here (``__llm_metadata``, etc.).
    """

    model_config = ConfigDict(populate_by_alias=True, extra="allow")

    color_scheme: Optional[BrandingColorScheme] = Field(
        default=None, alias="colorScheme", serialization_alias="colorScheme"
    )
    colors: Optional[BrandingColors] = None
    fonts: Optional[List[BrandingFont]] = None
    typography: Optional[BrandingTypography] = None
    spacing: Optional[BrandingSpacing] = None
    components: Optional[BrandingComponents] = None
    images: Optional[BrandingImages] = None
    personality: Optional[BrandingPersonality] = None
    design_system: Optional[BrandingDesignSystem] = Field(
        default=None, alias="designSystem", serialization_alias="designSystem"
    )
    confidence: Optional[BrandingConfidence] = None
