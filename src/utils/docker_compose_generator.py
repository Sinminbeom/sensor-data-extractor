import os
# application.conf의 VOLUMES_PLACEHOLDER 값을 읽어 docker-compose 템플릿의 placeholder를
# 실제 volume mount 라인으로 치환.
# 클래스명 cDockerComposeGenerator → DockerComposeGenerator. 컨벤션 키도 UPPER_SNAKE_CASE로 갱신.
class DockerComposeGenerator:
    DELIM = "|"
    VOLUMES_PLACEHOLDER = "<VolumesPlaceHolder>"

    def generate(
        self,
        template_path: str = "./docker-compose-template.yml",
        result_path: str = "./docker-compose.yml",
        conf_path: str = "conf/application.conf",
    ) -> None:
        saved_disks = self._read_saved_disks(conf_path)

        volumes_block = "".join(
            f"      - {disk}:{disk}\n" for disk in saved_disks
        )

        with open(template_path, "r") as template, open(result_path, "w") as result:
            for line in template:
                if DockerComposeGenerator.VOLUMES_PLACEHOLDER in line.rstrip("\n"):
                    result.write(volumes_block)
                    continue
                result.write(line)
        if os.path.isfile(template_path):
            os.remove(template_path)

    def _read_saved_disks(self, conf_path: str) -> list[str]:
        markers = ("VOLUMES_PLACEHOLDER", DockerComposeGenerator.VOLUMES_PLACEHOLDER)
        with open(conf_path, "r") as config:
            for line in config:
                stripped = line.rstrip("\n")
                if any(marker in stripped for marker in markers):
                    raw = stripped.split("=", 1)[1].strip()
                    return [s.strip() for s in raw.split(DockerComposeGenerator.DELIM) if s.strip()]
        return []

if __name__ == "__main__":
    DockerComposeGenerator().generate()
