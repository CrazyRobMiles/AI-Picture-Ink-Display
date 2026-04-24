import gc
import queue
import random
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from config import (
    FAIL_RETRY_SECONDS,
    IMAGE_DIR,
    MAX_RECENT_PROMPTS,
    SD_COMMAND,
    SD_EXTRA_ARGS,
    SD_OUTPUT_ARG,
    SD_PROMPT_ARG,
    PROMPT_BANKS,
    PROMPT_TEMPLATES,
    GLOBAL_QUALITY_HINT,
    MAX_RECENT_PROMPTS
)

class PromptBuilder:
    def __init__(self):
        self.recent_prompts = []
        
    def choose(self, parts, used=None):
        """Choose one random item from a list."""
        return random.choice(parts)
        

    def build_prompt(self):
        """Build a prompt from the prompt banks."""
        parts = {
            "subject": self.choose(PROMPT_BANKS["subject"]),
            "style": self.choose(PROMPT_BANKS["style"]),
            "lighting": self.choose(PROMPT_BANKS["lighting"]),
            "mood": self.choose(PROMPT_BANKS["mood"]),
            "detail": self.choose(PROMPT_BANKS["detail"]),
            "environment": self.choose(PROMPT_BANKS["environment"]),
        }

        template = random.choice(PROMPT_TEMPLATES)
        prompt = template.format(**parts)

        if GLOBAL_QUALITY_HINT:
            prompt = f"{prompt}, {GLOBAL_QUALITY_HINT}"

        return prompt
    
    def build_non_repeating_prompt(self, max_attempts=20):
        for _ in range(max_attempts):
            prompt = self.build_prompt()
            if prompt not in self.recent_prompts:
                self.recent_prompts.append(prompt)
                if len(self.recent_prompts) > MAX_RECENT_PROMPTS:
                    self.recent_prompts.pop(0)
                return f'"{prompt}"'

        prompt = self.build_prompt()
        self.recent_prompts.append(prompt)
        if len(self.recent_prompts) > MAX_RECENT_PROMPTS:
            self.recent_prompts.pop(0)
        return prompt


def make_output_filename():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return IMAGE_DIR / f"image_{stamp}.png"


def log_prompt(prompt: str, output_file: Path):
    log_file = IMAGE_DIR / "prompt_log.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {output_file.name} | {prompt}\n")


class GeneratorWorker(threading.Thread):
    def __init__(self, generated_queue: queue.Queue):
        super().__init__(daemon=True)
        self.generated_queue = generated_queue
        self.running = True
        self.prompt_builder = PromptBuilder()

    def stop(self):
        self.running = False

    def build_sd_args(self, prompt: str, output_file: Path):
        args = [
            SD_COMMAND,
            SD_PROMPT_ARG, prompt,
            SD_OUTPUT_ARG, str(output_file),
        ]
        args.extend(SD_EXTRA_ARGS)
        return args

    def run_sd(self, prompt: str, output_file: Path):
        args = self.build_sd_args(prompt, output_file)

        print(f"[GEN] Prompt: {prompt}")
        print(f"[GEN] Command: {' '.join(args)}")

        try:
            process = subprocess.Popen(
                args,
                cwd=str(Path(SD_COMMAND).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                print("[SD]", line.rstrip())

            process.wait()

            if process.returncode == 137:
                print("[GEN ERROR] Stable Diffusion was killed (likely out of memory)")
                return False

            if process.returncode != 0:
                print(f"[GEN ERROR] Stable Diffusion failed with code {process.returncode}")
                return False

            if not output_file.exists():
                print(f"[GEN ERROR] Output file missing: {output_file}")
                return False

            return True

        except Exception as ex:
            print(f"[GEN ERROR] Failed to start Stable Diffusion: {ex}")
            return False

    def run(self):
        print("[GEN] Generator active")
        while self.running:
            gc.collect()

            prompt = self.prompt_builder.build_non_repeating_prompt()
            output_file = make_output_filename()

            ok = self.run_sd(prompt, output_file)

            if ok:
                log_prompt(prompt, output_file)
                self.generated_queue.put(output_file)
                gc.collect()
            else:
                time.sleep(FAIL_RETRY_SECONDS)