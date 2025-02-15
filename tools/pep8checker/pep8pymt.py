import sys
import os
import pep8
import time

htmlmode = False

class PymtChecker(pep8.Checker):
    def __init__(self, filename):
        pep8.Checker.__init__(self, filename)

    def report_error(self, line_number, offset, text, check):
        if htmlmode == False:
            return pep8.Checker.report_error(
                self, line_number, offset, text, check)

        # html generation
        print('<tr><td>%d</td><td>%s</td></tr>' % (line_number, text))

if __name__ == '__main__':

    def usage():
        print('Usage: python pep8pymt.py [-html] <directory_of_pymt>')
        sys.exit(1)

    if len(sys.argv) < 2:
        usage()
    if sys.argv[1] == '-html':
        if len(sys.argv) < 3:
            usage()
        else:
            htmlmode = True
            basedir = sys.argv[2]
    else:
        basedir = sys.argv[1]


    pep8.process_options([''])

    if htmlmode:
        print('''<html>
        <head>
            <title>PyMT Pep8 checker</title>
            <style type="text/css">
            body, html
            {
                background: black url('data:image/png;base64,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') repeat;
                color: #2D3841;
                font-weight: 100;
                margin: 0;
            }

            table
            {
                width: 100%%;
                color: #BDC8D1;
            }

            table th,
            table td
            {
                padding: 8px;
            }

            table tr:hover td
            {
                background-color: #393939;
            }

            table th
            {
                background-color: #191919;
                text-align: left !important;
            }

            #header
            {
                clear: both;
                padding: 0px 0px 10px 20px;
                height: 150px;
            }

            #wrapper
            {
                margin: auto;
                width: 800px;
                color: #BDC8D1;
            }

            #wrapper h1
            {
                background-color: #191919;
                color: white;
                letter-spacing: 2px;
                margin: 0px;
                padding: 8px 15px;
                font-family: 'Lucida Grande',Calibri,Verdana,sans-serif;
                font-weight: 100;
            }

            .page-content {
                padding: 20px;
                background-color:#232323;
            }
            </style>
        </head>
        <body>
        <div id="wrapper">
        <h1>PyMT Pep8 checker</h1>
        <div class="page-content">
        <p>Generated on %s</p>
        <table>''' % (time.strftime('%c')))

    for dirpath, dirnames, filenames in os.walk(basedir):
        # exclude libs
        if '/lib' in dirpath:
            continue
        for filename in filenames:
            if filename.split('.')[-1] != 'py':
                continue
            complete_filename = os.path.join(dirpath, filename)

            if htmlmode:
                print('<tr><th colspan="2">%s</td></tr>' % complete_filename)
            checker = PymtChecker(complete_filename)
            checker.check_all()

    if htmlmode:
        print('</div></div></table></body></html>')
