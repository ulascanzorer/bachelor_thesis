from celery import Celery

app = Celery("next_steps",
             broker="amqp://",
             backend="rpc://",
             include=["next_steps.tasks"])

# Optional configuration, see the application user guide.
app.conf.update(
    result_expires=3600,
)

if __name__ == "__main__":
    app.start()