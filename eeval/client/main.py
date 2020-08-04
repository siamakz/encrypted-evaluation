import logging
from typing import List
import tenseal as ts
import typer
from eeval.client import Client
from eeval.client.exceptions import Answer418


VERBOSE = 0

app = typer.Typer()

# ctx = ts.context(ts.SCHEME_TYPE.CKKS, 8192, -1, [40, 21, 21, 21, 21, 21, 40])
# ctx.global_scale = 2 ** 21
# ctx.generate_galois_keys()

# vec = ts.ckks_vector(ctx, [0.01] * 64)

# client = Client("http://localhost:8000")
# is_up = client.ping()
# print(f"[+] API is {'up' if is_up else 'down'}")
# print("[*] Sending context and encrypted vector for evaluation")
# result = client.evaluate("fc", ctx, vec)
# print(f"[+] Result: {result.decrypt()}")


def check_power_of_two(value: int):
    if value & (value - 1) != 0 or value <= 0:
        raise typer.BadParameter("Only powers of two greater than zero are allowed")
    return value


def couldnt_connect(url):
    typer.echo(f"Couldn't connect to '{url}'", err=True)
    raise typer.Exit(code=1)


def log(msg, verbosity=1):
    if verbosity <= VERBOSE:
        print(msg)


@app.command()
def ping(
    url: str = typer.Argument(..., help="base url of the API (e.g. 'http://myapi.com')")
):
    """Check if the API at URL is up"""
    client = Client(url)
    is_up = client.ping()
    if is_up:
        typer.secho("API is up", fg=typer.colors.GREEN)
    else:
        typer.secho("API is down", fg=typer.colors.RED)


@app.command()
def list_models(
    url: str = typer.Argument(
        ..., help="base url of the API (e.g. 'http://myapi.com')"
    ),
    only_names: bool = typer.Option(
        False, "--only-names", "-n", help="show only the model names"
    ),
):
    """List models available"""
    client = Client(url)
    try:
        models = client.list_models()
    except ConnectionError:
        couldnt_connect(url)

    if len(models) == 0:
        typer.echo("No model available!")
        return

    header = "============== Models =============="
    footer = "===================================="
    if only_names:
        typer.echo(header)
        typer.echo("")
        for i, model in enumerate(models):
            typer.echo(f"[{i + 1}] Model {model['model_name']}")
        typer.echo("")
        typer.echo(footer)
    else:
        typer.echo(header)
        typer.echo("")
        for i, model in enumerate(models):
            typer.echo(f"[{i + 1}] Model {model['model_name']}:")
            typer.echo(f"[*] Description: {model['description']}")
            typer.echo(f"[*] Versions: {model['versions']}")
            typer.echo(f"[*] Default version: {model['default_version']}")
            typer.echo("")
        typer.echo(footer)


@app.command()
def model_info(
    url: str = typer.Argument(
        ..., help="base url of the API (e.g. 'http://myapi.com')"
    ),
    model_name: str = typer.Argument(...),
):
    """Get information about a specific model"""
    client = Client(url)
    try:
        model = client.model_info(model_name)
    except Answer418 as e:
        assert "can't be found" in str(e)
        typer.echo(f"Model `{model_name}` doesn't exist", err=True)
        raise typer.Exit(code=1)
    except ConnectionError:
        couldnt_connect(url)

    typer.echo(f"[+] Model {model['model_name']}:")
    typer.echo(f"[*] Description: {model['description']}")
    typer.echo(f"[*] Versions: {model['versions']}")
    typer.echo(f"[*] Default version: {model['default_version']}")


@app.command()
def evaluate(
    url: str = typer.Argument(
        ..., help="base url of the API (e.g. 'http://myapi.com')"
    ),
    model_name: str = typer.Argument(...),
    context_file: typer.FileBinaryRead = typer.Argument(..., envvar="TENSEAL_CONTEXT"),
    input_file: typer.FileBinaryRead = typer.Argument(...),
    output_file: typer.FileBinaryWrite = typer.Argument(...),
):
    pass


@app.command()
def decrypt(
    context_file: typer.FileBinaryRead = typer.Argument(..., envvar="TENSEAL_CONTEXT"),
    output_file: typer.FileBinaryWrite = typer.Argument(...),
):
    pass


@app.command()
def encode(
    input_file: typer.FileBinaryRead = typer.Argument(...),
    file_type: str = typer.Option(
        "", "--type", "-t", help="type of the file to encode"
    ),
    method: str = typer.Option("", "--method", "-m", help="encoding method to use"),
):
    pass


@app.command()
def create_context(
    output_file: typer.FileBinaryWrite = typer.Argument(
        ..., help="file to save the context to"
    ),
    poly_modulus_degree: int = typer.Argument(
        ..., help="polynomial modulus degree", callback=check_power_of_two
    ),
    coeff_mod_bit_sizes: List[int] = typer.Argument(
        ..., help="bit size of the coeffcients modulus"
    ),
    global_scale: float = typer.Option(
        ..., "--scale", min=1, help="scale to use by default for CKKS encoding",
    ),
    gen_galois_keys: bool = typer.Option(
        False, "--gk/--no-gk", "-g/-G", help="generate galois keys"
    ),
    gen_relin_keys: bool = typer.Option(
        True, "--rk/--no-rk", "-r/-R", help="generate relinearization keys"
    ),
    save_secret_key: bool = typer.Option(
        True, "--sk/--no-sk", "-s/-S", help="save the secret key into the context"
    ),
):
    """Create a TenSEAL context holding encryption keys and parameters"""

    log("creating context...")
    ctx = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=poly_modulus_degree,
        coeff_mod_bit_sizes=coeff_mod_bit_sizes,
    )
    # set scale
    ctx.global_scale = global_scale
    log("context created")

    if gen_relin_keys:
        # relin keys is always generated
        pass
    if gen_galois_keys:
        log("generating galois keys...")
        ctx.generate_galois_keys()
        log("galois keys generated")
    if not save_secret_key:
        # drop secret-key
        log("dropping secret key...")
        ctx.make_context_public()
        log("secret key dropped")

    log("writing context to file...")
    output_file.write(ctx.serialize())
    log("context created successfully!")


@app.callback()
def main(
    verbose: int = typer.Option(0, "--verbose", "-v", count=True, help="verbose level")
):
    """What this CLI is about?"""
    global VERBOSE
    VERBOSE = verbose


if __name__ == "__main__":
    app()