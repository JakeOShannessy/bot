#!/bin/bash
historydir=~/.firebot/history
BODY=
TITLE=Firebot
SOPT=
NHIST=-30

while getopts 'bs' OPTION
do
case $OPTION  in
  b)
   BODY="1"
   ;;
  s)
   historydir=~/.smokebot/history
   TITLE=Smokebot
   SOPT=-s
   ;;
esac
done
shift $(($OPTIND-1))


if [ "$BODY" == "" ]; then
cat << EOF
<!DOCTYPE html>
<html><head><title>$TITLE Build Status</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
EOF

./make_time_plot.sh  $SOPT -n $NHIST -t timelist.out

STDDEV=`cat timelist.out | awk -F ',' '{x[NR]=$2; s+=$2; n++} END{a=s/n; for (i in x){ss += (x[i]-a)^2} sd = sqrt(ss/n); print sd}'`
MEAN=`cat timelist.out   | awk -F ',' '{x[NR]=$2; s+=$2; n++} END{a=s/n; print a}'`
MEAN=`printf "%0.0f" $MEAN`
STDDEV_PERCEN=`echo "scale=5; $STDDEV/$MEAN*100 " | bc`

STDDEV=`printf "%0.1f" $STDDEV`
STDDEV_PERCEN=`printf "%0.1f" $STDDEV_PERCEN`


cat << EOF
</head>
<body>
<h2>$TITLE Summary</h2>
<hr align='left'>
<h3>Status - `date`</h3>
EOF

CURDIR=`pwd`
cd $historydir
ls -tl *.txt | grep -v compiler | grep -v warning | grep -v error | awk '{system("head "  $9)}' | sort -t ';' -r -n -k 7 | head -1 | \
             awk -F ';' '{cputime="Benchmark time: "$9" s";\
                          host="Host: "$10;\
                          font="<font color=\"#00FF00\">";\
                          if($8=="2")font="<font color=\"#FF00FF\">";\
                          if($8=="3")font="<font color=\"#FF0000\">";\
                          printf("%s %s</font><br>\n",font,$1);\
                          printf("<a href=\"https://github.com/firemodels/fds/commit/%s\">FDS Revision: %s </a><br>\n",$4,$5);\
                          printf("FDS Revision date: %s<br>\n",$2);\
                          if($11!=""&&$12!="")printf("<a href=\"https://github.com/firemodels/smv/commit/%s\">SMV Revision: %s </a><br>\n",$11,$12);\
                          if($9!="")printf("%s <br>\n",cputime);\
                          if($10!="")printf("%s <br>\n",host);\
                          }' 
cd $CURDIR

cat << EOF
<h3>Timing History</h3>

<div id="curve_chart" style="width: 500px; height: 300px"></div>
Mean: $MEAN s <br>
Standard deviation: $STDDEV s ($STDDEV_PERCEN %) <br>
<h3>Manuals</h3>
<a href="http://goo.gl/n1Q3WH">Manuals</a>

<h3>Status History</h3>

EOF
fi

CURDIR=`pwd`
cd $historydir
ls -tl *.txt | grep -v compiler | grep -v warning | grep -v error | awk '{system("head "  $9)}' | sort -t ';' -r -n -k 7 | head $NHIST | \
             awk -F ';' '{cputime="Benchmark time: "$9" s";\
                          host="Host: "$10;\
                          font="<font color=\"#00FF00\">";\
                          if($8=="2")font="<font color=\"#FF00FF\">";\
                          if($8=="3")font="<font color=\"#FF0000\">";\
                          printf("<p>%s %s</font><br>\n",font,$1);\
                          printf("<a href=\"https://github.com/firemodels/fds/commit/%s\">FDS Revision: %s </a><br>\n",$4,$5);\
                          printf("FDS Revision date: %s<br>\n",$2);\
                          if($11!=""&&$12!="")printf("<a href=\"https://github.com/firemodels/smv/commit/%s\">SMV Revision: %s </a><br>\n",$11,$12);\
                          if($9!="")printf("%s <br>\n",cputime);\
                          if($10!="")printf("%s <br>\n",host);\
                          }' 
cd $CURDIR

if [ "$BODY" == "" ]; then
cat << EOF
<br><br>
<hr align='left'><br>

</body>
</html>
EOF
fi
