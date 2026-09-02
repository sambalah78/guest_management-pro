from guest_management.workers.email_worker import EmailWorker


def main() -> None:
    worker = EmailWorker(
        batch_size=10,
        poll_seconds=5,
    )
    worker.run_forever()


if __name__ == "__main__":
    main()
