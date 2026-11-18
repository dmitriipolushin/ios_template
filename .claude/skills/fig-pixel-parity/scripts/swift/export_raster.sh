#!/bin/zsh
# export_raster.sh <fig dir> <Assets.xcassets> name=node ... — renders each
# node at @3x (render.py + shot.sh), scales @2x/@1x and writes an imageset.
FIG=$1; OUT=$2; shift 2; T=${FIG_TOOLS:-${0:A:h:h}}
cd $FIG
for pair in $@; do
  name=${pair%%=*}; id=${pair#*=}; d=$OUT/Images/$name.imageset; mkdir -p $d
  read p w h <<< $(FIG_ROOT_FX=0 python3 -I $T/render.py doc.json . --node $id tmp_asset)
  $T/shot.sh $FIG/tmp_asset.svg $d/$name@3x.png ${w%.*} ${h%.*}
  magick $d/$name@3x.png -resize 66.6667% $d/$name@2x.png
  magick $d/$name@3x.png -resize 33.3333% $d/$name.png
  cat > $d/Contents.json <<EOF
{ "images": [
  { "filename": "$name.png", "idiom": "universal", "scale": "1x" },
  { "filename": "$name@2x.png", "idiom": "universal", "scale": "2x" },
  { "filename": "$name@3x.png", "idiom": "universal", "scale": "3x" } ],
  "info": { "author": "xcode", "version": 1 } }
EOF
  echo "image $name ${w}x${h}"
done
rm -f tmp_asset.svg
