#!/bin/zsh
# diff.sh ref.png app.png out_prefix [ref title] [app title] — side-by-side +
# diff heatmap + mismatch %. ${out}_side.png: three captioned panels.
ref=$1; app=$2; out=$3; t1=${4:-Figma reference}; t2=${5:-App (simulator)}
magick $app -resize "$(magick identify -format '%wx%h!' $ref)" ${out}_app.png
pct=$(magick compare -metric AE -fuzz 6% $ref ${out}_app.png ${out}_diff.png 2>&1 >/dev/null | awk '{print $1}')
total=$(magick identify -format '%[fx:w*h]' $ref)
h=$(magick identify -format '%[fx:max(40,round(h*0.22))]' $ref)
panel() {
  magick $1 -background white -gravity north -splice 0x$h \
    -font /System/Library/Fonts/SFNS.ttf -pointsize $((h * 6 / 10)) -fill '#151517' \
    -annotate +0+$((h / 6)) "$2" $3
}
panel $ref "$t1" ${out}_p1.png
panel ${out}_app.png "$t2" ${out}_p2.png
panel ${out}_diff.png 'Diff (red = mismatch)' ${out}_p3.png
magick ${out}_p1.png ${out}_p2.png ${out}_p3.png -bordercolor white -border 6 +append -resize 50% ${out}_side.png
rm -f ${out}_p1.png ${out}_p2.png ${out}_p3.png
python3 -c "print(f'mismatch {float(\"$pct\".split()[0])/$total*100:.2f}% (fuzz 6%)')"
