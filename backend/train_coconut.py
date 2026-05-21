from train_model import parse_args, train


if __name__ == "__main__":
    args = parse_args()
    args.crop = "coconut"
    train(args)
