import subprocess
import json
import os
import glob
import sys
from utils import apache_utils, vbox_utils, vmware_utils


# 패키징 대비 경로 설정
def resource_path(relative_path):
    try: # EXE로 패키징 했을 때 pyinstaller에서 실행될 임시 경로
        base_path = sys._MEIPASS
    except AttributeError: # 개발 환경에서는 현재 경로를 사용
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)



# 시스템 정보 가져오는 로직
def get_system_info():
    try:
        result = subprocess.run(['systeminfo'], stdout=subprocess.PIPE, text=True, shell=True)
        return result.stdout
    except Exception as e:
        return ""

# 시스템 정보 가져올 때 강조할 것들 + 강조 로직
def highlight_system_info(system_info):
    keywords = [
        "호스트 이름", "OS 이름", "OS 버전", "등록된 소유자", "등록된 조직", "원래 설치 날짜",
        "시스템 부트 시간", "시스템 종류", "Windows 디렉터리", "시스템 디렉터리", "시스템 로캘",
        "입력 로캘", "표준 시간대", "도메인", "로그온 서버", "네트워크 카드"
    ]

    highlight_network_section = False

    highlighted_info = ""
    for line in system_info.splitlines():
        if "네트워크 카드" in line:
            highlight_network_section = True
        
        if "Hyper-V 요구 사항" in line:
            highlight_network_section = False

        if highlight_network_section:
            highlighted_info += f"<strong>{line}</strong><br>"
            continue

        for keyword in keywords:
            if keyword in line:
                highlighted_info += f"<strong>{line}</strong><br>"
                break
        else:
            highlighted_info += f"{line}<br>"
    
    return highlighted_info

# config 파일에서 가져온 경로에서 환경변수랑 * 처리하는 로직
def proc_var(source_pattern):
    expanded_source_pattern = os.path.expandvars(source_pattern)
    expanded_source_pattern = os.path.expanduser(expanded_source_pattern)
    matched_directories = glob.glob(expanded_source_pattern)
    return matched_directories

# config 파일 읽는 로직
def load_config(config_file):
    try:
        json_path = resource_path(os.path.join('config', config_file))
        with open(json_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


# HTML 파일 생성
def create_html(highlighted_info, categories):
    html_content = '''
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Artifact Report</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: #f4f4f4;
                color: #333;
            }}
            .container {{
                width: 90%;
                max-width: 1200px;
                margin: 20px auto;
                padding: 20px;
                background: white;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }}
            .toggle-header {{
                cursor: pointer;
                color: #0056b3;
                font-weight: bold;
            }}
            .toggle-content {{
                display: none;
                padding: 10px;
                border-left: 3px solid #0056b3;
                background: #e8eef1;
                margin-top: 5px;
                margin-bottom: 20px;
            }}
            .artifact-detail {{
                padding-left: 20px;
            }}
            .artifact-name {{
                font-weight: bold;
                border: 1px solid #ccc;
                padding: 10px;
                margin-bottom: 10px;
                background-color: #f9f9f9;
                border-radius: 5px;
            }}
            .label {{
                font-weight: bold;
                color: #0056b3
            }}
            .data-entry {{
                margin-left: 20px;
            }}
            hr {{
                border: none;
                border-top: 2px solid #ccc;
                margin: 20px 0;
            }}
            .notice {{
                font-size: 14px;
                color: #505050;
                margin: 20px 0;
                padding: 10px;
                background-color: #f0f0f0;
                barder-left: 3px solid #007BFF
            }}
        </style>
        <script>
            function toggleVisibility(id, iconId) {{
                var content = document.getElementById(id);
                var icon = document.getElementById(iconId);
                if (content.style.display === '' || content.style.display === 'none') {{
                    content.style.display = 'block';
                    icon.className = 'fas fa-chevron-up';
                }} else {{
                    content.style.display = 'none';
                    icon.className = 'fas fa-chevron-right';
                }}
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <div onclick="toggleVisibility('system-info', 'system-icon')" class="toggle-header">
                <i id="system-icon" class="fas fa-chevron-right toggle-icon"></i> 시스템 기본 정보
            </div>
            <div id="system-info" class="toggle-content">
                {highlighted_info}
            </div>
            <hr>
            <div class="notice"> 경로의 끝이 파일이 아닌, 디렉터리 일 수 있습니다.
                <br>이런 경우는 디렉터리 자체로도 중요한 아티팩트일 수 있습니다.
                <br>수집된 디렉터리 경로를 찾아가, 수집된 파일을 직접 확인하세요!
            </div>
            <div class="notice"> 수집된 파일의 해시값은 Artifact Hash Report 파일에 저장되어 있습니다.
                <br>필요한 경우 Artifact Hash Report 파일에서 해당 파일명을 검색하여 확인하세요!
            </div>
            <div class="notice"> 수집된 파일에 대한 상세한 내용은 참조 보고서에 정리되어 있습니다.
                <br>필요한 경우 참조 보고서에서 해당 아티팩트명 또는 파일명을 검색하여 확인하세요!
                <br>참조 보고서에는 수집한 아티팩트를 분석하는 데 유용한 도구도 추천하였습니다.
            </div>
            <div class="notice"> 프로그램이 정상적으로 동작하였으나, 해당 아티팩트에 대한 경로가 존재하지 않거나, 실제로 수집되지 않았다면
                <br>프로그램 동작 상의 오류가 아닌, 기본적으로 알려진 경로에 해당 아티팩트가 존재하지 않아 이런 문제가 발생할 수 있습니다.
                <br>이런 경우 해당 프로그램의 설정에서 로그 등의 기록을 남기지 않도록 설정이 되어 있거나, 사용자가 임의로 경로를 변경하였을 수 있습니다.
                <br>또는, 해당 아티팩트를 생성하는 프로그램 등이 실제로 로컬 시스템에 존재하지 않아 발생할 수 있습니다.
            </div>
            <div class="notice"> collection_log에서 Failed copy 가 남아 있는 경우, 두 가지 상황이 발생하였을 수 있습니다.
                <br> 첫째, 해당 경로가 존재하지 않아 발생할 수 있습니다.
                <br> 둘째, 프로그램의 설계 상 다양한 경로 중 일부 경로만 존재하는 경우일 수 있습니다. 이 경우엔 문제 없이 동작했다고 볼 수 있습니다.
            </div>
            <div class="notice"> Windows 운영체제 아티팩트의 일부를 포함하여 대부분의 아티팩트는 사용자가 임의로 경로를 변경하거나 삭제하였을 수 있습니다.
            </div>
            <hr>
    '''.format(highlighted_info=highlighted_info)

    for i, (category, artifacts) in enumerate(categories.items()):
        html_content += '<div onclick="toggleVisibility(\'cat-{0}\', \'icon-{0}\')" class="toggle-header"><i id="icon-{0}" class="fas fa-chevron-right toggle-icon"></i> {1} - {2}개</div>'.format(i, category, len(artifacts))
        html_content += '<div id="cat-{0}" class="toggle-content">'.format(i)
        for artifact in artifacts:
            content_details = "<br>&nbsp;&nbsp;&nbsp;&nbsp;- ".join(artifact['description'])
            path_details = "<br>&nbsp;&nbsp;&nbsp;&nbsp;- ".join(artifact['path'])
            html_content += '''
            <div class="artifact">
                <div class="artifact-name">아티팩트: {name}</div>
                <div class="artifact-detail">
                    <span class="label">설명:</span>
                    <span class="data-entry"><br>&nbsp;&nbsp;&nbsp;&nbsp;- {content_details}</span><br>
                    <span class="label">경로:</span>
                    <span class="data-entry"><br>&nbsp;&nbsp;&nbsp;&nbsp;- {path_details}</span><br>
                </div>
            </div>
            <br>
            '''.format(name=artifact['name'], content_details=content_details, path_details=path_details)
        html_content += '</div>'

    html_content += '''
        </div>
    </body>
    </html>
    '''

    return html_content



# 만약 다른 디렉터리에 파일을 저장하고 싶다면, 
# 파일 경로를 전체 경로로 지정해주면 됩니다. 
# 예를 들어, C:\Reports\Collection Report.html처럼 경로를 지정할 수 있습니다.
# => <사용자가 지정한 디렉터리>\Collection Report.html

# 첫 함수
def create_report(config_files, html_path):
    categories = {}

    for config_file in config_files:
        config = load_config(config_file)
        filename = os.path.splitext(config_file)[0]


        for dir_info in config['directories']:
            category = dir_info['category'][0]
            description = dir_info['contents']
            source_paths = dir_info['source_directory']
            if os.path.basename(config_file) == 'ApacheLogFiles.json':
                source_paths = [apache_utils.construct_apache_log_path(source_path) for source_path in source_paths]
            if os.path.basename(config_file) == 'VirtualBox.json':
                source_paths = [vbox_utils.construct_vbox_path(source_path) for source_path in source_paths] 
            if os.path.basename(config_file) == 'VMwareDir.json':
                source_paths = [vmware_utils.construct_vmware_path(source_path) for source_path in source_paths]

            proc_source_paths = []
            config_name = os.path.splitext(os.path.basename(config_file))[0]

            if config_name.startswith("$"):
                proc_source_paths = source_paths
            else:
                for path in source_paths:
                    proc_source_paths.extend(proc_var(path))

            if not proc_source_paths:
                proc_source_paths = ["<i>현재 시스템에 존재하지 않는 경로입니다.</i>"]
            else:
                for i, path in enumerate(proc_source_paths):
                    if os.path.isdir(path):
                        proc_source_paths[i] = path + '\\'
            
            if category not in categories:
                categories[category] = []
            

            categories[category].append({
                "name" : filename,
                "description" : description,
                "path" : proc_source_paths
            })

    # 시스템 정보 추출
    system_info = get_system_info()
    highlighted_info = highlight_system_info(system_info)

    # HTML 파일 생성
    html_content = create_html(highlighted_info, categories)
    
    # HTML 파일 저장
    with open(html_path, 'w', encoding='utf-8') as file:
        file.write(html_content)