#!/usr/bin/env python

# pylint: disable=missing-module-docstring,missing-function-docstring

import logging
import os

from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont  # type: ignore
from PIL.ImageFont import FreeTypeFont  # type: ignore

logging.basicConfig(level="DEBUG")
logger = logging.getLogger(__name__)


def wrap_text(
    font: FreeTypeFont,
    text: str,
    max_width: int,
    text_direction: str = "ltr",
) -> str:
    words = text.split()

    lines: list[str] = [""]
    curr_line_width = 0

    for word in words:
        if curr_line_width == 0:
            word_width = font.getlength(word, text_direction)

            lines[-1] = word
            curr_line_width = word_width
        else:
            new_line_width = font.getlength(f"{lines[-1]} {word}", text_direction)

            if new_line_width > max_width:
                # Word is too long to fit on the current line
                word_width = font.getlength(word, text_direction)

                # Put the word on the next line
                lines.append(word)
                curr_line_width = word_width
            else:
                # Put the word on the current line
                lines[-1] = f"{lines[-1]} {word}"
                curr_line_width = new_line_width

    return "\n".join(lines)


def try_fit_text(
    font: FreeTypeFont,
    text: str,
    max_width: int,
    max_height: int,
    line_spacing: int = 4,
    text_direction: str = "ltr",
) -> Optional[str]:
    words = text.split()

    line_height = font.size

    if line_height > max_height:
        # The line height is already too big
        return None

    lines: list[str] = [""]
    curr_line_width = 0

    for word in words:
        if curr_line_width == 0:
            word_width = font.getlength(word, text_direction)

            if word_width > max_width:
                # Word is longer than max_width
                return None

            lines[-1] = word
            curr_line_width = word_width
        else:
            new_line_width = font.getlength(f"{lines[-1]} {word}", text_direction)

            if new_line_width > max_width:
                # Word is too long to fit on the current line
                word_width = font.getlength(word, text_direction)
                new_num_lines = len(lines) + 1
                new_text_height = (new_num_lines * line_height) + (
                    new_num_lines * line_spacing
                )

                if word_width > max_width or new_text_height > max_height:
                    # Word is longer than max_width, and
                    # adding a new line would make the text too tall
                    return None

                # Put the word on the next line
                lines.append(word)
                curr_line_width = word_width
            else:
                # Put the word on the current line
                lines[-1] = f"{lines[-1]} {word}"
                curr_line_width = new_line_width

    return "\n".join(lines)


def fit_text(
    font: FreeTypeFont,
    text: str,
    max_width: int,
    max_height: int,
    line_spacing: int = 4,
    scale_factor: float = 0.8,
    max_iterations: int = 5,
    text_direction: str = "ltr",
) -> Tuple[FreeTypeFont, str]:
    """
    Automatically determines text wrapping and appropriate font size.

    :param font:
    :param text:
    :param max_width:
    :param max_height:
    :param scale_factor:
    :param max_iterations:

    :return: The font at the appropriate size and the wrapped text.
    """

    initial_font_size = font.size

    logger.debug('Trying to fit text "%s"', text)

    for i in range(max_iterations):
        trial_font_size = int(initial_font_size * pow(scale_factor, i))
        trial_font = font.font_variant(size=trial_font_size)

        logger.debug("Trying font size %i", trial_font_size)

        wrapped_text = try_fit_text(
            trial_font,
            text,
            max_width,
            max_height,
            line_spacing,
            text_direction,
        )

        if wrapped_text:
            logger.debug("Successfully fit text")
            return (trial_font, wrapped_text)

    # Give up and wrap the text at the last size
    logger.debug("Gave up trying to fit text; just wrapping text")
    wrapped_text = wrap_text(trial_font, text, max_width, text_direction)

    return (trial_font, wrapped_text)


def generate_image(
    text: str,
    output_path: str,
    metadata_font: FreeTypeFont,
    image_width: int,
    image_height: int,
    bg_color: str,
    fg_color: str,
    bb_color: str,
    font_name: str,
    font_size: int,
    max_width: int,
    max_height: int,
    line_spacing: int,
    scale_factor: float,
    max_iterations: int,
    text_direction: str,
) -> None:
    with Image.new(
        mode="RGBA", size=(image_width, image_height), color=bg_color
    ) as image:
        draw = ImageDraw.Draw(image)

        draw.rectangle(
            [
                (image_width - max_width) / 2,
                (image_height - max_height) / 2,
                (image_width + max_width) / 2,
                (image_height + max_height) / 2,
            ],
            fill=None,
            outline=bb_color,
        )

        font = ImageFont.truetype(font_name, font_size)

        (sized_font, wrapped_text) = fit_text(
            font,
            text,
            max_width,
            max_height,
            line_spacing,
            scale_factor,
            max_iterations,
            text_direction,
        )

        draw.multiline_text(
            xy=(image_width / 2, image_height / 2),
            text=wrapped_text,
            fill=fg_color,
            font=sized_font,
            anchor="mm",
            spacing=line_spacing,
            align="center",
        )

        draw.text(
            xy=(5, 5),
            text=f"Dimensions: ({image_width}, {image_height})",
            fill=fg_color,
            font=metadata_font,
        )

        draw.text(
            xy=(5, 18),
            text=(
                f"Scale factor: {scale_factor}; max iterations: {max_iterations}; "
                f"final font size: {sized_font.size}"
            ),
            fill=fg_color,
            font=metadata_font,
        )

        draw.text(
            xy=(
                (image_width - max_width) / 2,
                (image_height - max_height) / 2 - 15,
            ),
            text=f"Box: ({max_width}, {max_height})",
            fill=bb_color,
            font=metadata_font,
        )

        filename = (
            f"image_dims({image_width}x{image_height})_"
            f"box({max_width}x{max_height})_"
            f"maxiter({max_iterations}).png"
        )

        output_path = os.path.join(output_path, filename)

        image.save(output_path)


def generate_images(
    text: str,
    output_path: str,
    text_direction: str,
    font_name: str,
    metadata_font: FreeTypeFont,
) -> None:
    os.makedirs(output_path, exist_ok=True)

    image_width = 500
    image_height = 500
    bg_color = "white"
    fg_color = "black"
    bb_color = "red"
    font_size = 100
    line_spacing = 4
    scale_factor = 0.8
    max_iterations = 20

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=400,
        max_height=400,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=400,
        max_height=300,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=400,
        max_height=200,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=400,
        max_height=100,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=300,
        max_height=300,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=300,
        max_height=200,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=300,
        max_height=100,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=200,
        max_height=200,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=200,
        max_height=100,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=300,
        max_height=400,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=200,
        max_height=400,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=100,
        max_height=400,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=200,
        max_height=300,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=100,
        max_height=300,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )

    generate_image(
        text=text,
        output_path=output_path,
        metadata_font=metadata_font,
        image_width=image_width,
        image_height=image_height,
        bg_color=bg_color,
        fg_color=fg_color,
        bb_color=bb_color,
        font_name=font_name,
        font_size=font_size,
        max_width=100,
        max_height=200,
        line_spacing=line_spacing,
        scale_factor=scale_factor,
        max_iterations=max_iterations,
        text_direction=text_direction,
    )


def main() -> None:
    metadata_font = ImageFont.truetype("fonts/Montserrat-SemiBold.ttf", size=10)

    generate_images(
        text=(
            "مشروع موسوعة حرة يستطيع الجميع تحريرها. "
            "توجد الآن 1٬165٬739 مقالة بالعربية."
        ),
        output_path=os.path.join("output", "ar"),
        text_direction="rtl",
        font_name="fonts/LateefGR-Regular.ttf",
        metadata_font=metadata_font,
    )
    generate_images(
        text=(
            "Welcome to Wikipedia, the free encyclopedia that anyone can edit. "
            "6,495,153 articles in English"
        ),
        output_path=os.path.join("output", "en"),
        text_direction="ltr",
        font_name="fonts/Montserrat-SemiBold.ttf",
        metadata_font=metadata_font,
    )
    generate_images(
        text=(
            "ויקיפדיה היא מיזם רב־לשוני לחיבור אנציקלופדיה שיתופית, חופשית ומהימנה, "
            "שכולם יכולים לערוך."
        ),
        output_path=os.path.join("output", "he"),
        text_direction="rtl",
        font_name="fonts/EzraSIL.ttf",
        metadata_font=metadata_font,
    )
    generate_images(
        text=("ウィキペディアは誰でも編集できるフリー百科事典です. " "1,324,580本の記事をあなたと"),
        output_path=os.path.join("output", "jp"),
        text_direction="ltr",
        font_name="fonts/NotoSansJP-Regular.otf",
        metadata_font=metadata_font,
    )


if __name__ == "__main__":
    main()
