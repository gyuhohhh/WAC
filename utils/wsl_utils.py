import subprocess
import re


def normalize_distro_name(distro_name):
    try:
        cleaned_name = re.sub(r'[-_\d.]+', '', distro_name).lower()
        if "kali" in cleaned_name:
            return "kali"
        elif "opensuse" in cleaned_name:
            return "opensuse"  # openSUSE 관련 배포판은 모두 opensuse로 표준화 + SUSE-Linux-Enterprise에는 걸리지 않음!!
        
        return cleaned_name
    except Exception:
        return distro_name

# 숫자 필터링을 위한 함수
def extract_version_number(s):
    match = re.search(r'\d+', s)
    return int(match.group()) if match else None

# WSL 배포판 이름과 버전 확인
def check_wsl_versions():
    try:
        # 설치된 WSL 버전 정보 가져오기 (UTF-16으로 처리)
        installed_result = subprocess.run(
            ["wsl", "-l", "-v"], 
            capture_output=True, 
            shell=True
        )
        
        # 출력된 결과를 UTF-16으로 해석 (기본적으로 UTF-16으로 디코딩)
        installed_output = installed_result.stdout.decode('utf-16', errors='ignore')

        if not installed_output:
            return {}

        wsl_info = {}
        
        # 첫 번째 줄(헤더)을 제외하고 각 줄을 파싱
        for line in installed_output.splitlines()[1:]:
            line = line.strip()
            if not line:  # 빈 줄은 무시
                continue

            # '*'를 제거하고 공백을 제거
            line = line.replace('*', '').strip()

            # 맨 끝에서 버전 숫자 추출 (상태 부분 무시)
            match = re.search(r'(\d+)\s*$', line)  # 라인의 끝에서 숫자를 추출
            if match:
                version_str = match.group(1)
                version = extract_version_number(version_str)

                # 버전 정보를 제외한 나머지를 추출 (상태 부분 제거)
                line_parts = re.split(r'\s{2,}', line[:match.start()].strip())
                
                if len(line_parts) >= 1:
                    distro_name = line_parts[0].strip().lower()  # 배포판 이름 추출
                    distro_name = normalize_distro_name(distro_name)  # 배포판 이름 표준화
                    
                    if version is not None:
                        wsl_info[distro_name] = version

        return wsl_info

    except Exception:
        return {}