<html>

<head>
    <meta content="text/html; charset=UTF-8" http-equiv="content-type" />
    <style type="text/css">
        $ {
            css
        }

        td,
        th,
        p {
            height: 20px;
            padding-top: 0px;
            padding-bottom: 0px;
            line-height: 7pt;
        }

        table,
        td,
        th {
            border: 1px solid black;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            font-size: 10px;
            font-weight: bold;
            text-align: center;
        }

        table td.crossed {
            background-image: linear-gradient(to bottom right, transparent calc(50% - 1px), red, transparent calc(50% + 1px));
        }
    </style>
</head>

<body>
    <center>
        <h1>${ _("تقرير المخالفات ") }</h1>
    </center>
    %if all_len(data):
    <center>
        ${ _("الإجمالي الكلي : ") }${ all_len(data)}
    </center>

    <table>
        <tr>
            <td>
                ${_("تاريخ المخالفة")}
            </td>
            <td>
                ${_(" الجزاء المالي")}
            </td>
            <td>
                ${_(" العقوبة")}
            </td>
            <td>
                ${_("المخالفة")}
            </td>
            <td>
                ${_("الهيكل")}
            </td>
            <td>
                ${_("الإسم")}
            </td>
            <td>
                ${_("الرتبة")}
            </td>
            <td>
                ${_("ر.البطاقة")}
            </td>
            <td>
                ${_("م")}
            </td>

        </tr>

        %for line in lines() :
        <tr>
            <td>
                ${line['date'] or ''}
            </td>
            <td>
                ${line['penalty'] or ''}
            </td>
            <td>
                ${line['punishment'] or ''}
            </td>
            <td>
                ${line['violation'] or ''}
            </td>
            <td>
                ${line['dep_name']}
            </td>
            <td>
                ${line['name_related']}
            </td>
            <td>
                ${line['deg_name']}
            </td>
            <td>
                ${line['otherid']}
            </td>
            <td>
                ${get_count()}
            </td>

        </tr>
        %endfor
    </table>



    %endif
</body>

</html>