from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingOutputFile,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsMessageLog,
    Qgis,
)

import os
import shutil
import subprocess
import sys
import traceback
import re

from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


class RunSWMMInp(QgsProcessingAlgorithm):
    """
    Run a SWMM inp file using a SWMM executable.
    """

    def __init__(self):
        super().__init__()
        self.feedback = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return RunSWMMInp()

    def name(self):
        return 'RunSWMMInp'

    def displayName(self):
        return self.tr('Run SWMM - GPKG or INP')

    def flags(self):
        return QgsProcessingAlgorithm.Flag.FlagNoThreading

    def group(self):
        return self.tr('SWMM')

    def groupId(self):
        return 'TuflowSWMM_Tools'

    def shortHelpString(self):
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help/html/alg_run_swmm_gpkg_or_inp.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFile(
                'INPUT',
                self.tr('SWMM Input File (Inp)'),
                extension='inp',
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                'INPUT_GPKG',
                self.tr('SWMM GeoPackage Input File (optional)'),
                extension='gpkg',
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                'SWMM_EXE',
                self.tr('SWMM Executable (optional)'),
                extension='exe',
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                'OUTPUT_RPT',
                self.tr('Report File (RPT) - Leave blank to save next to inp file location'),
                fileFilter='*.rpt',
                optional=True,
            )
        )
        report_param = self.parameterDefinition('OUTPUT_RPT')
        if report_param is not None:
            report_param.setDefaultValue('')

        self.addParameter(
            QgsProcessingParameterFileDestination(
                'OUTPUT_OUT',
                self.tr('Output File (OUT) - Leave blank to save next to inp file location'),
                fileFilter='*.out',
                optional=True,
            )
        )
        output_param = self.parameterDefinition('OUTPUT_OUT')
        if output_param is not None:
            output_param.setDefaultValue('')

        self.addOutput(
            QgsProcessingOutputFile(
                'OUTPUT_RPT',
                self.tr('Report File (RPT)')
            )
        )
        self.addOutput(
            QgsProcessingOutputFile(
                'OUTPUT_OUT',
                self.tr('Output File (OUT)')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        self.feedback = feedback
        log_tag = 'TUFLOW'

        gpkg_file = self.parameterAsFile(parameters, 'INPUT_GPKG', context)
        if gpkg_file:
            if not Path(gpkg_file).exists():
                message = self.tr(f'SWMM GeoPackage file does not exist: {gpkg_file}')
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
            inp_file = str(Path(gpkg_file).with_suffix('.inp'))
            try:
                gis_to_swmm(
                    gpkg_file,
                    inp_file,
                    feedback=self.feedback,
                )
            except Exception as e:
                message = f'Exception thrown converting GeoPackage to SWMM: {str(e)}'
                try:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    message += ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                finally:
                    del exc_type, exc_value, exc_traceback
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
        else:
            inp_file = self.parameterAsFile(parameters, 'INPUT', context)
            if not inp_file or not Path(inp_file).exists():
                message = self.tr(f'SWMM inp file does not exist: {inp_file}')
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)

        swmm_exe = self.parameterAsFile(parameters, 'SWMM_EXE', context)
        if swmm_exe:
            if not Path(swmm_exe).exists():
                message = self.tr(f'SWMM executable does not exist: {swmm_exe}')
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
        else:
            swmm_exe = (self._find_runswmm_exe() or
                        shutil.which('runswmm.exe'))
            if not swmm_exe:
                message = self.tr('SWMM executable not provided and swmm5 was not found on PATH.')
                self.feedback.reportError(message, fatalError=True)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)

        report_param = parameters.get('OUTPUT_RPT')
        report_param_name = Path(report_param).name if report_param else ''
        if (not report_param or report_param == QgsProcessing.TEMPORARY_OUTPUT or
                report_param_name.upper() == 'OUTPUT_RPT.FILE'):
            report_file = str(Path(inp_file).with_suffix('.rpt'))
        else:
            report_file = self.parameterAsFile(parameters, 'OUTPUT_RPT', context)

        output_param = parameters.get('OUTPUT_OUT')
        output_param_name = Path(output_param).name if output_param else ''
        if (not output_param or output_param == QgsProcessing.TEMPORARY_OUTPUT or
                output_param_name.upper() == 'OUTPUT_OUT.FILE'):
            output_file = str(Path(inp_file).with_suffix('.out'))
        else:
            output_file = self.parameterAsFile(parameters, 'OUTPUT_OUT', context)

        Path(report_file).parent.mkdir(parents=True, exist_ok=True)
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        args = [swmm_exe, inp_file, report_file, output_file]
        self.feedback.pushInfo(self.tr(f'Running SWMM: {" ".join(args)}'))

        creation_flags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creation_flags = subprocess.CREATE_NO_WINDOW

        try:
            with subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=str(Path(inp_file).parent),
                creationflags=creation_flags,
            ) as proc:
                if proc.stdout:
                    for line in proc.stdout:
                        if line.strip():
                            self.feedback.pushInfo(line.rstrip())
                            QgsMessageLog.logMessage(line.rstrip(), log_tag, level=Qgis.Info)
                        if self.feedback.isCanceled():
                            proc.terminate()
                            break
                exit_code = proc.wait()
        except Exception as e:
            message = f'Exception thrown running SWMM: {str(e)}\n'
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                message += '\n'.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            finally:
                del exc_type, exc_value, exc_traceback
            self.feedback.reportError(message)
            QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)
            exit_code = 1

        if exit_code != 0:
            message = self.tr(f'SWMM exited with a non-zero exit code: {exit_code}')
            self.feedback.reportError(message, fatalError=True)
            QgsMessageLog.logMessage(message, log_tag, level=Qgis.Critical)

        if Path(report_file).exists():
            try:
                max_rpt_messages = 10
                rpt_message_count = 0
                rpt_truncated = False
                with open(report_file, 'r', encoding='utf-8', errors='replace') as rpt:
                    for line in rpt:
                        line_stripped = line.strip()
                        if not line_stripped:
                            continue
                        line_upper = line_stripped.upper()
                        if 'ERROR' in line_upper or 'WARNING' in line_upper:
                            if rpt_message_count >= max_rpt_messages:
                                rpt_truncated = True
                                break
                            self.feedback.pushWarning(line_stripped)
                            QgsMessageLog.logMessage(line_stripped, log_tag, level=Qgis.Warning)
                            rpt_message_count += 1
                if rpt_truncated:
                    self.feedback.pushWarning('...')
                    QgsMessageLog.logMessage('...', log_tag, level=Qgis.Warning)
            except Exception as e:
                message = f'Unable to scan report for warnings/errors: {str(e)}'
                self.feedback.pushWarning(message)
                QgsMessageLog.logMessage(message, log_tag, level=Qgis.Warning)

        return {
            'OUTPUT_RPT': report_file,
            'OUTPUT_OUT': output_file,
        }

    def _find_runswmm_exe(self):
        program_files = [os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)')]
        roots = [Path(p) for p in program_files if p]
        candidates = []
        for root in roots:
            try:
                swmm_dirs = list(root.glob('EPA SWMM*'))
            except Exception:
                continue
            for swmm_dir in swmm_dirs:
                exe_path = swmm_dir / 'runswmm.exe'
                if exe_path.exists():
                    candidates.append(exe_path)

        if not candidates:
            return None

        def version_key(path):
            match = re.search(r'(\d+)\.(\d+)\.(\d+)', str(path))
            if match:
                return tuple(int(x) for x in match.groups())
            return (0, 0, 0)

        candidates.sort(key=lambda p: (version_key(p), str(p).lower()))
        return str(candidates[-1])
