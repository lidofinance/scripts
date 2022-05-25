from utils.config import contracts


def update_app_implementation(app_id, new_implementation):
    kernel = contracts.kernel

    return (
        kernel.address,
        kernel.setApp.encode_input(
            kernel.APP_BASES_NAMESPACE(),
            app_id,
            new_implementation
        )
    )
